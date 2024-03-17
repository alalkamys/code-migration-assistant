from app.config import app_config

from github import Github
from github.Auth import Auth
from github.GithubException import BadCredentialsException
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException
from github.GithubObject import _NotSetType as NotSetType
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.Repository import Repository
from typing import Any
from typing import Union
import logging

_logger = logging.getLogger(app_config.APP_NAME)


def get_pulls(
    base_url: str,
    repo_full_name: str,
    base: str,
    head: str,
    auth: Auth,
    user_agent: str,
    state: str = "open"
) -> PaginatedList[PullRequest] | None:
    """Retrieve pull requests from a GitHub repository.

    Args:
        base_url (str): The base URL of the GitHub instance.
        repo_full_name (str): The full name of the repository (e.g., 'owner/repo').
        base (str): The base branch of the pull request.
        head (str): The head branch of the pull request.
        auth (Auth): Authentication credentials for GitHub.
        user_agent (str): The user agent for making HTTP requests.
        state (str, optional): The state of the pull request. Defaults to "open".

    Returns:
        PaginatedList[PullRequest] | None: A list of pull request objects, or None if unsuccessful.
    """
    try:
        _logger.debug("Instantiating a GitHub client..")
        github = Github(
            base_url=base_url,
            auth=auth,
            user_agent=user_agent
        )

        _logger.info(f"Searching for repository '{repo_full_name}'..")
        repo = github.get_repo(full_name_or_id=repo_full_name)

        _logger.info(f"Repository '{repo_full_name}' found")

        owner_or_org = repo_full_name.split('/')[0]

        _logger.info(f"Querying {state} pull requests with base '{
                     base}' and head '{owner_or_org}:{head}'...")
        pulls = repo.get_pulls(state=state, base=base,
                               head=f"{owner_or_org}:{head}")

        _logger.info(
            f"Found '{pulls.totalCount}' {state} pull requests matching the criteria")

        if pulls.totalCount > 0:
            _logger.debug(f"Pull Requests IDs: {
                [f"PR #{pull.number}" for pull in pulls]}")

        return pulls

    except BadCredentialsException as bad_creds_exc:
        error_msg = str(bad_creds_exc).strip()
        if '401' in error_msg:
            _logger.error(
                "Authentication error: Make sure 'GITHUB_TOKEN' contains a valid Personal Access Token (PAT).")
        elif '403' in error_msg:
            _logger.error(
                "Bad credentials: Make sure 'GITHUB_TOKEN' contains a valid PAT with the required access.")
        else:
            _logger.error(f"Unexpected BadCredentialsException: {error_msg}")

    except UnknownObjectException:
        _logger.error(
            f"'{repo_full_name}' repository not found or '{github.get_user().login}' doesn't have access to it. Make sure to include a valid repo")

    except GithubException as github_exc:
        error_msg = str(github_exc).strip()
        if '422' in error_msg and '"field": "base"' in error_msg:
            _logger.error(f"Invalid base ref: '{
                          base}'. Make sure to include a valid 'base' ref in pullRequest.github.base")
        elif '403' in error_msg and "Resource protected by organization SAML enforcement" in error_msg:
            _logger.error(f"Forbidden: '{
                          repo_full_name}' Resource protected by organization SAML enforcement. You must grant your Personal Access token access to an organization within this enterprise.")
        else:
            _logger.error(f"Unexpected GithubException: {error_msg}")

    return None


def create_pulls(
    base_url: str,
    repo_full_name: str,
    pull_request_payload: dict[str, Any],
    user_agent: str,
    auth: Auth
) -> PullRequest:
    """Creates a pull request on GitHub.

    Args:
        base_url (str): The base URL of the GitHub instance.
        repo_full_name (str): The full name of the repository (e.g., 'owner/repo').
        pull_request_payload (dict): The payload containing pull request details.
        user_agent (str): The user agent for making HTTP requests.
        auth (Auth): Authentication credentials for GitHub.

    Returns:
        PullRequest | None: The created pull request object, or None if unsuccessful.
    """
    try:
        pull_request: Union[PullRequest, None] = None

        _logger.debug("Instantiating a github client..")
        github = Github(base_url=base_url,
                        auth=auth,
                        user_agent=user_agent)

        _logger.info(f"Searching for '{repo_full_name}'..")
        repo: Repository = github.get_repo(full_name_or_id=repo_full_name)

        _logger.info(f"Repository '{repo_full_name}' found")

        _logger.info("Creating pull request...")
        pull_request = repo.create_pull(
            title=pull_request_payload["title"],
            body=pull_request_payload.get('body', NotSetType()),
            base=pull_request_payload["base"],
            head=pull_request_payload["head"],
            maintainer_can_modify=pull_request_payload.get(
                'maintainer_can_modify', NotSetType())
        )

        _logger.info(f"Pull request created successfully with ID '{
                     pull_request.number}'")

    except BadCredentialsException as bad_creds_exc:
        error_msg = str(bad_creds_exc).strip()
        if '401' in error_msg:
            _logger.error("Authentication error: Make sure 'GITHUB_TOKEN' with a valid PAT. You can check the documentation at 'https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api' for more information")
        elif '403' in error_msg:
            _logger.error("Bad credentials: Make sure 'GITHUB_TOKEN' with a valid PAT with the required access. You can check the documentation at 'https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api' for more information")
        else:
            _logger(f"Unexpected BadCredentialsException: {error_msg}")

    except UnknownObjectException:
        _logger.error(
            f"'{repo_full_name}' repository not found or '{github.get_user().login}' doesn't have access to it. Make sure to include a valid repo")

    except GithubException as github_exc:
        error_msg = str(github_exc).strip()
        if '422' in error_msg and 'pull request already exists' in error_msg:
            base = pull_request_payload['base']
            head = pull_request_payload['head']
            owner_or_org = repo_full_name.split('/')[0]
            state = 'open'
            pulls = repo.get_pulls(state=state, base=base, head=f"{
                                   owner_or_org}:{head}")
            _logger.debug(f"'{repo_full_name}' already has '{
                          pulls.totalCount}' '{state}' pulls")
            _logger.debug(f"pulls numbers: {[pull.number for pull in pulls]}")
            _logger.error(f"A pull request with ID '{pulls[0].number}' already exists for '{repo_full_name}' repository for base:head '{
                          pull_request_payload["base"]}:{pull_request_payload["head"]}'")
        elif '422' in error_msg and '"field": "base"' in error_msg:
            _logger.error(f"Invalid base ref: '{
                          pull_request_payload["base"]}'. Make sure to include a valid 'base' ref in pullRequest.github.base")
        elif '403' in error_msg and "Resource protected by organization SAML enforcement" in error_msg:
            _logger.error(f"Forbidden: '{repo_full_name}' Resource protected by organization SAML enforcement. You must grant your Personal Access token access to an organization within this enterprise. You can check the documentation at 'https://docs.github.com/articles/authenticating-to-a-github-organization-with-saml-single-sign-on/' for more information")
        else:
            _logger.error(f"Unexpected GithubException: {error_msg}")

    return pull_request
