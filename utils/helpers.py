from config import app_config
from config import RemoteProgressReporter

from azure.devops.connection import Connection
from azure.devops.credentials import BasicAuthentication
from azure.devops.exceptions import AzureDevOpsAuthenticationError
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_0.git import GitPullRequest
from azure.devops.v7_0.git import GitRepository
from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import GitPullRequestSearchCriteria
from git import Actor
from git import Repo
from git.refs.head import Head
from git.remote import PushInfo
from git.remote import PushInfoList
from git.exc import GitCommandError
from git.exc import NoSuchPathError
from github import Auth as auth
from github import Github
from github.Auth import Auth
from github.GithubException import BadCredentialsException
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException
from github.GithubObject import _NotSetType as NotSetType
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from github.Repository import Repository
from msrest.exceptions import ClientRequestError
from typing import Any
from typing import List, Union
from typing import Union
from urllib import parse
import json
import logging
import os
import re
import sys

_logger = logging.getLogger(app_config.APP_NAME)


def load_targets_config(file_path: str) -> dict[str, Any]:
    """Load configuration from a JSON file.

    Args:
        file_path (str): The path to the JSON configuration file.

    Returns:
        dict: A dictionary containing the loaded configuration.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        json.JSONDecodeError: If the JSON content is not valid.
        Exception: For any other unexpected error during loading.
    """
    try:
        file_abspath = os.path.abspath(file_path)
        with open(file_abspath) as f:
            _logger.info(f"Loading '{file_abspath}'")
            return json.load(f)

    except FileNotFoundError:
        error_message = f"Configuration file '{
            file_abspath}' not found."

    except json.JSONDecodeError:
        error_message = f"Unable to load configuration from '{
            file_abspath}'. Invalid JSON format."

    except Exception as e:
        error_message = f"An unexpected error occurred while loading '{
            file_abspath}': {str(e).strip()}"

    _logger.error(error_message)
    _logger.info("Exiting..")
    sys.exit(1)


def load_target_repos(repos: list[dict]) -> list[Repo]:
    """Load target repositories.

    Args:
        repos (list[dict]): A list of dictionaries containing repository information.

    Returns:
        list[Repo]: A list of GitPython Repo objects representing the loaded repositories.
    """
    result = []
    for repo in repos:
        try:
            repo_type = repo['type'].strip().lower()
            repo_name = repo['name']
            scm_provider_data: dict[str, str] = repo['scmProvider']
            if repo_type == 'local':
                _logger.info(f"'{repo_name}' is a 'Local' repository. Using..")
                repo_obj = Repo(path=repo['source'])
            elif repo_type == 'remote':
                _logger.info(
                    f"'{repo_name}' is a 'Remote' repository. Cloning..")
                repo_obj = Repo.clone_from(url=repo['source'], to_path=os.path.join(
                    app_config.REMOTE_TARGETS_CLONING_PATH, repo_name))
            scm_provider_type = scm_provider_data['type'].strip(
            ).lower().replace(' ', '')
            if scm_provider_type == "azuredevops":
                _logger.debug(f"'{scm_provider_type}' SCM provider detected")
                repo_obj.scm_provider = {
                    'type': scm_provider_type,
                    'base_url': scm_provider_data['baseUrl'],
                    'project': scm_provider_data['project']
                }
            elif scm_provider_type == "github":
                _logger.debug(f"'{scm_provider_type}' SCM provider detected")
                repo_obj.scm_provider = {
                    'type': scm_provider_type,
                    'domain': scm_provider_data['domain'],
                    'owner_or_org': scm_provider_data['ownerOrOrg'].strip()
                }
            result.append(repo_obj)
        except GitCommandError as git_cmd_err:
            if git_cmd_err.status == 128 and 'already exists' in git_cmd_err.stderr:
                repo_abspath = os.path.abspath(os.path.join(
                    app_config.REMOTE_TARGETS_CLONING_PATH, repo_name))
                _logger.info(f"'{repo_abspath}' already exists, using..")
                repo_obj = Repo(path=repo_abspath)
                scm_provider_type = scm_provider_data['type'].strip(
                ).lower().replace(' ', '')
                if scm_provider_type == "azuredevops":
                    _logger.debug(
                        f"'{scm_provider_type}' SCM provider detected")
                    repo_obj.scm_provider = {
                        'type': scm_provider_type,
                        'base_url': scm_provider_data['baseUrl'],
                        'project': scm_provider_data['project']
                    }
                elif scm_provider_type == "github":
                    _logger.debug(
                        f"'{scm_provider_type}' SCM provider detected")
                    repo_obj.scm_provider = {
                        'type': scm_provider_type,
                        'domain': scm_provider_data['domain'],
                        'owner_or_org': scm_provider_data['ownerOrOrg'].strip()
                    }
                result.append(repo_obj)
            else:
                _logger.error(f"Unexpected GitCommandError: {
                              str(git_cmd_err).strip()}")
        except NoSuchPathError:
            repo_abspath = os.path.abspath(os.path.join(
                app_config.REMOTE_TARGETS_CLONING_PATH, repo_name))
            _logger.error(f"Invalid 'Local' repo source path '{
                repo_abspath}': No such path. Check '{repo_name}' source path")
        except Exception as e:
            _logger.error(f"Unexpected error when loading '{
                          repo_name}': {str(e).strip()}")
    return result


def identity_setup(repo: Repo, actor_username: str, actor_email: str) -> None:
    """Set up identity configuration for a GitPython repository.

    Args:
        repo (Repo): The GitPython repository object.
        actor_username (str): The username to set.
        actor_email (str): The email address to set.

    Returns:
        bool: True if the identity configuration was set successfully, False otherwise.
    """
    try:
        config_writer = repo.config_writer()
        _logger.debug(f"Setting username to {actor_username}")
        config_writer.set_value('user', 'name', actor_username).release()
        _logger.debug(f"Setting email to <{actor_email}>")
        config_writer.set_value('user', 'email', actor_email).release()
        del (config_writer)
        return True
    except Exception as e:
        _logger.error(f"An error occurred while setting up identity configuration: {
                      str(e).strip()}")
        return False


def checkout_branch(repo: Repo, branch_name: str, from_branch: str = None) -> bool:
    """Checkout or create a new branch in the local repository.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        branch_name (str): The name of the branch to checkout or create.
        from_branch (str, optional): The name of the base branch to create the new branch from.
            If None, create the new branch from the current branch. Defaults to None.

    Returns:
        bool: True if the branch was successfully checked out or created, False otherwise.
    """
    try:
        if branch_name in repo.branches:
            _logger.info(
                f"'{branch_name}' branch already exists, checking out..")
            branch = repo.branches[branch_name]
        else:
            _logger.info(f"'{branch_name}' doesn't exist, creating..")
            from_branch = from_branch or repo.active_branch.name
            if from_branch in repo.branches:
                branch = repo.create_head(branch_name, commit=from_branch)
                _logger.info(f"Created new branch '{
                    branch_name}' based on '{from_branch}' branch")
            else:
                _logger.error(
                    f"Error: '{from_branch}' based on branch doesn't exist")
                return False

        branch.checkout()
        _logger.info(f"Checked out branch '{branch_name}' successfully.")
        return True

    except GitCommandError as e:
        _logger.error(f"'git-checkout' command error: {str(e).strip()}")

    except Exception as e:
        _logger.error(f"Unexpected error while checking out to '{
                      branch_name}': {str(e).strip()}")

    return False


# TODO: find a way to determine if the end result contains some errors but were skipped
def search_and_replace(directory: str, patterns: dict, excluded_files: list[str] = [], hidden_dirs: bool = False) -> dict[str, dict[str, Any]] | None:
    """Searches all files in a directory (including subdirectories) for patterns and replaces them.

    Args:
        directory (str): The directory path to search for files.
        patterns (dict): A dictionary where keys are patterns to search for and values are replacements.
        excluded_files (list, optional): A list of filenames to exclude from the search. Defaults to [].
        hidden_dirs (bool, optional): Whether to include hidden directories in the search. Defaults to False.

    Returns:
        Union[Dict[str, Dict[str, Any]], None]: A dictionary containing information about the number of matches found for each pattern.
            The dictionary structure is as follows:
            {
                'pattern1': {'count': <int>, 'match': {'file1': <int>, 'file2': <int>, ...}},
                'pattern2': {'count': <int>, 'match': {'file3': <int>, 'file4': <int>, ...}},
                ...
            }
            Returns None if an error occurs during the search and replace operation.
    """
    result = {pattern: {'count': 0, 'match': {}}
              for pattern in patterns.keys()}
    if hidden_dirs:
        _logger.info("Including hidden directories in the search")
    if len(excluded_files) > 0:
        _logger.info(
            f"Excluding {(' '.join("'" + f + "'" for f in excluded_files))} file(s) from the search")
    try:
        repo_name = os.path.basename(os.path.normpath(directory))
        for root, dirs, files in os.walk(directory):
            if not hidden_dirs:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            if len(excluded_files) > 0:
                files_root_relpath = [os.path.join(repo_name, os.path.relpath(
                    os.path.join(root, f), directory)) for f in files]
                files[:] = [
                    os.path.basename(os.path.normpath(f)) for f in files_root_relpath if not f in tuple(excluded_files)]
            for file in files:
                file_path = os.path.join(root, file)
                file_relpath = os.path.relpath(file_path, directory)
                _logger.info(
                    f"Searching '{file_relpath}'")
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', "ignore")
                except Exception as e:
                    _logger.error(f"Error reading file '{
                                  file_relpath}': {str(e)}")
                    _logger.info("Skipping..")
                    continue
                updated_content = content
                for pattern, replacement in patterns.items():
                    try:
                        matches = re.findall(pattern, content)
                        if matches:
                            _logger.info(
                                f"A match was found for pattern '{pattern}'")
                            result[pattern]['match'][file_relpath] = len(
                                matches)
                            result[pattern]['count'] += len(matches)
                        updated_content = re.sub(
                            pattern, replacement, updated_content)
                    except re.error as regex_error:
                        _logger.error(f"Error in regex pattern '{
                                      pattern}': {regex_error}")
                if updated_content != content:
                    try:
                        _logger.info("Replacing..")
                        with open(file_path, 'w') as f:
                            f.write(updated_content)
                    except Exception as ex:
                        _logger.error(f"Error writing to file '{
                                      file_relpath}': '{str(ex)}'")
        return result
    except Exception as ex:
        _logger.error(f"An unexpected error occurred: '{str(ex)}'")
        return None


def commit_changes(repo: Repo, title: str, description: str = None, author: Actor = None, committer: Actor = None, auto_stage: bool = False) -> bool:
    """Commit changes to the repository.

    Args:
        repo (Repo): The GitPython repository object.
        title (str): The title of the commit.
        description (str, optional): The description of the commit. Defaults to None.
        author (Actor, optional): The author of the commit. Defaults to None.
        committer (Actor, optional): The committer of the commit. Defaults to None.
        auto_stage (bool, optional): Whether to automatically stage all changes before committing. Defaults to False.

    Returns:
        bool: True if changes were successfully committed, False otherwise.
    """
    try:
        if auto_stage:
            _logger.debug("'auto_stage' mode enabled.")
            _logger.debug("Staging modified/deleted files..\n")
            repo.git.add(u=True)
        commit_message = title
        if description:
            commit_message += f"\n{description}"
        _logger.debug("Commit Details:")
        _logger.debug("---------------")
        _logger.debug(f"Title: {title}")
        if description:
            _logger.debug(f"Description: {description}")
        if author:
            _logger.debug(f"Author: {author.name} <{author.email}>")
        if committer:
            _logger.debug(f"Committer: {committer.name} <{committer.email}>")
        _logger.debug(f"Commit Message: {commit_message}")
        _logger.info("Committing changes..")
        repo.index.commit(commit_message, author=author, committer=committer)
        _logger.info("Changes committed successfully.")
        return True
    except Exception as e:
        _logger.error(f"An error occurred while committing changes: {
                      str(e).strip()}")
        return False


def push_changes(repo: Repo, remote_name: str = 'origin', remote_branch_name: str | None = None, timeout: int | None = 180) -> bool:
    """Push changes to the remote repository.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        remote_name (str, optional): The name of the remote repository to push changes to. Defaults to 'origin'.
        remote_branch_name (str | None, optional): The name of the remote branch to push changes to. 
            If None, the active local branch's name is used. Defaults to None.
        timeout (int | None, optional): The timeout (in seconds) for the push operation. Defaults to 180.

    Returns:
        bool: True if the push operation is successful, False otherwise.

    Raises:
        IndexError: If the specified remote repository does not exist.
        AssertionError: If the specified remote is not valid or if the push operation fails.

    Notes:
        This function pushes changes from the active local branch to the specified remote branch. 
        It handles various scenarios such as existing and non-existing remotes, and provides detailed logging 
        information during the push operation. The timeout parameter allows customization of the maximum time 
        allowed for the push operation.

    Example:
        # Push changes from the active branch to the 'main' branch of the remote repository 'origin'
        repo = Repo("/path/to/local/repository")
        push_changes(repo, remote_name='origin', remote_branch_name='main')
    """
    try:
        assert repo.remotes[remote_name].exists()
        remote = repo.remotes[remote_name]
        branch_name = repo.active_branch.name
        remote_branch_name = remote_branch_name if remote_branch_name else branch_name
        _logger.info(f"Pushing changes to '{
                     remote_branch_name}' branch of remote '{remote_name}'...")
        result: PushInfoList = remote.push(
            refspec=f"{branch_name}:{remote_branch_name}", progress=RemoteProgressReporter(_logger), kill_after_timeout=timeout)
        try:
            assert len(result) != 0
            VALID_PUSH_INFO_FLAGS: list[int] = [PushInfo.FAST_FORWARD, PushInfo.NEW_HEAD,
                                                PushInfo.UP_TO_DATE, PushInfo.FORCED_UPDATE, PushInfo.NEW_TAG]
            for push_info in result:
                _logger.debug("+------------+")
                _logger.debug("| Push Info: |")
                _logger.debug("+------------+")
                _logger.debug(f"Flag: {push_info.flags}")
                _logger.debug(f"Local ref: {push_info.local_ref}")
                _logger.debug(f"Remote Ref: {push_info.remote_ref}")
                _logger.debug(f"Remote ref string: {
                    push_info.remote_ref_string}")
                _logger.debug(f"Old Commit: {push_info.old_commit}")
                _logger.debug(f"Summary: {push_info.summary.strip()}")
                if push_info.flags not in VALID_PUSH_INFO_FLAGS:
                    if push_info.flags == PushInfo.ERROR:
                        _logger.error(
                            f"Incomplete push error: Push contains rejected heads. Check your internet connection and run in 'debug' mode to see more details.")
                    else:
                        _logger.error(
                            "Unexpected push error, maybe the remote rejected heads. Check your internet connection and run in 'debug' mode to see more details.")
                    return False
        except AssertionError:
            _logger.error(f"Pushing changes to remote '{
                          remote_name}' completely failed. Check your internet connection and run in 'debug' mode to see the remote push progress.")
            return False
        _logger.info(f"Changes pushed successfully to '{
            branch_name}' branch of remote '{remote_name}'.")

        _logger.debug(f"Setting '{branch_name}' upstream branch to '{remote_name}/{
                      remote_branch_name}'..")
        repo.active_branch.set_tracking_branch(
            repo.refs[f"{remote_name}/{remote_branch_name}"])
        return True
    except IndexError:
        _logger.error(f"Error accessing remote '{
                      remote_name}': No such remote")
        return False
    except AssertionError:
        _logger.error(
            f"'{remote_name}' is not a valid remote. Valid remotes have an entry in the repository's configuration")
        return False


def get_pull_requests_azure_devops(
    base_url: str,
    project: str,
    repo_name: str,
    source_ref_name: str,
    target_ref_name: str,
    creds: BasicAuthentication,
    user_agent: str,
    status: str = 'active'
) -> Union[List[GitPullRequest], None]:
    """Get pull requests in Azure Repos based on source and target ref names.

    Args:
        base_url (str): The base URL of the Azure DevOps server.
        project (str): The name of the Azure DevOps project.
        repo_name (str): The name of the repository.
        source_ref_name (str): The source ref name.
        target_ref_name (str): The target ref name.
        creds (BasicAuthentication): The basic authentication credentials.
        status (str, optional): The pull request status. Default is 'active'.

    Returns:
        Union[List[GitPullRequest], None]: A list of open pull requests matching the criteria, or None if an error occurred.
    """
    try:
        _logger.debug("Instantiating Azure DevOps connection...")
        connection = Connection(base_url=base_url,
                                creds=creds,
                                user_agent=user_agent)

        _logger.debug("Instantiating a git client..")
        git_client: GitClient = connection.clients.get_git_client()

        _logger.info(f"Querying open pull requests with source ref name '{source_ref_name}' and target ref name '{
                     target_ref_name}' in '{parse.quote(f"{project}/{repo_name}")}'...")
        pull_requests: List[GitPullRequest] = git_client.get_pull_requests(
            project=project,
            repository_id=repo_name,
            search_criteria=GitPullRequestSearchCriteria(
                source_ref_name=source_ref_name,
                target_ref_name=target_ref_name,
                status=status
            )
        )

        _logger.info(f"Found '{len(pull_requests)
                               }' {status} pull requests matching the criteria")
        _logger.debug(f"Pull requests IDs: {
                      [pull_request.pull_request_id for pull_request in pull_requests]}")
        return pull_requests
    except Exception as e:
        _logger.error(
            f"An error occurred while querying pull requests: {str(e)}")
        return None


def raise_pull_request_azure_devops(
    base_url: str,
    project: str,
    repo_name: str,
    pull_request_payload: dict[str, Any],
    user_agent: str,
    creds: BasicAuthentication
) -> GitPullRequest | None:
    """Raise a pull request in Azure DevOps.

    Args:
        base_url (str): The base URL of the Azure DevOps service.
        project (str): The name of the project in which the repository resides.
        repo_name (str): The name of the repository for which the pull request is raised.
        pull_request_payload (dict[str, Any]): The payload containing the details of the pull request.
        creds (BasicAuthentication): The authentication credentials for Azure DevOps.

    Returns:
        GitPullRequest: The created pull request if successful, None otherwise.
    """
    try:
        _logger.debug("Creating Connection object..")
        connection = Connection(base_url=base_url,
                                creds=creds,
                                user_agent=user_agent)

        _logger.debug("Instantiating a git client..")
        git_client: GitClient = connection.clients.get_git_client()

        _logger.info(f"Searching for '{repo_name}' in '{project}' project..")
        target_repo: GitRepository = git_client.get_repository(project=project,
                                                               repository_id=repo_name)

        _logger.info(f"Repository '{repo_name}' found.")
        _logger.info("Creating pull request...")
        pull_request: GitPullRequest = git_client.create_pull_request(git_pull_request_to_create=pull_request_payload,
                                                                      repository_id=target_repo.id)

        _logger.info(
            f"Pull request created successfully with ID '{pull_request.pull_request_id}'.")
        return pull_request

    except AzureDevOpsServiceError as azure_devops_svc_err:
        error_msg = str(azure_devops_svc_err).strip()
        if 'project does not exist' in error_msg:
            _logger.error(
                f"'{project}' project doesn't exist. Verify that the name of the project is correct and that the project exists on the specified Azure DevOps Server")
        elif f"{repo_name} does not exist" in error_msg:
            _logger.error(
                f"'{repo_name}' repository does not exist or you do not have permissions for the operation you are attempting.")
        elif 'active pull request for the source and target branch already exists' in error_msg:
            _logger.error(
                "An active pull request for the source and target branch already exists")
        else:
            _logger.error(error_msg)
        return None

    except ClientRequestError:
        _logger.exception(
            f"'{base_url}' Request error: Make sure to add a valid URL")
        return None

    except AzureDevOpsAuthenticationError:
        _logger.exception(
            "Authentication error: Make sure you set 'AZURE_DEVOPS_PAT' with valid PAT")
        return None

    except Exception as e:
        _logger.error(
            f"Failed to create pull request: {str(e).strip()}")
        return None


def get_pull_requests_github(
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
        state (str, optional): The state of the pull request. Defaults to "open".

    Returns:
        PaginatedList[PaginatedList]: A list of pull request objects, or None if unsuccessful.
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

        _logger.debug(f"Pull Requests IDs: {[pull.number for pull in pulls]}")

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


def raise_pull_request_github(
    base_url: str,
    repo_full_name: str,
    pull_request_payload: dict[str, Any],
    user_agent: str,
    auth: Auth
) -> PullRequest:
    """Raise a pull request on GitHub.

    Args:
        base_url (str): The base URL of the GitHub instance.
        repo_full_name (str): The full name of the repository (e.g., 'owner/repo').
        pull_request_payload (dict): The payload containing pull request details.
        auth (Auth): Authentication credentials for GitHub.

    Returns:
        Optional[PullRequest]: The created pull request object, or None if unsuccessful.
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


def is_open_pull_requests(repo: Repo, pull_request_config: dict[str, dict[str, Any]]) -> tuple[bool, bool]:
    """
    Check if there is an open pull request for the given repository based on the SCM provider type.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        pull_request_config (dict[str, dict[str, Any]]): The configuration for the pull request, containing 'providerData' and 'payload'.

    Returns:
        tuple[bool, bool]: A tuple indicating whether there is an open pull request and if an error occurred.
    """
    try:
        scm_provider_data: dict[str, str] = repo.scm_provider
        scm_provider_type = scm_provider_data['type'].lower().strip()

        if scm_provider_type == "azuredevops":
            _logger.info("Azure DevOps pull request detected.")
            AZURE_DEVOPS_PAT = app_config.AZURE_DEVOPS_PAT

            if not AZURE_DEVOPS_PAT:
                _logger.error(
                    "Personal Access Token (PAT) not found. Please set 'AZURE_DEVOPS_PAT' environment variable with your Azure DevOps Personal Access Token (PAT) before running Code Migration Assistant")
                _logger.info("Aborting..")
                return False, False

            base_url = scm_provider_data['base_url'].strip()
            project = scm_provider_data['project'].strip()
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))

            pull_request_payload: dict[str,
                                       Any] = pull_request_config[scm_provider_type]

            source_ref_name = f"refs/heads/{
                repo.active_branch.name}"
            target_ref_name: str = pull_request_payload['targetRefName']

            if not target_ref_name.startswith("refs/heads/"):
                _logger.debug(
                    f"Updating targetRefName to 'refs/heads/{target_ref_name}'...")
                target_ref_name = f"refs/heads/{
                    target_ref_name}"

            pull_requests = get_pull_requests_azure_devops(base_url=base_url,
                                                           project=project,
                                                           repo_name=repo_name,
                                                           source_ref_name=source_ref_name,
                                                           target_ref_name=target_ref_name,
                                                           status="active",
                                                           user_agent=app_config.USER_AGENT,
                                                           creds=BasicAuthentication('PAT', AZURE_DEVOPS_PAT))
            if pull_requests is not None:
                is_open_pr = len(pull_requests) > 0
                is_err = False

            else:
                is_open_pr = False
                is_err = True

            return is_open_pr, is_err

        elif scm_provider_type == "github":
            _logger.info("GitHub pull request detected.")
            GITHUB_TOKEN = app_config.GITHUB_TOKEN

            if not GITHUB_TOKEN:
                _logger.error(
                    "GitHub API Key not found. Please set 'GITHUB_TOKEN' environment variable with your GitHub Personal Access Token (PAT) before running Code Migration Assistant")
                _logger.info("Aborting..")
                return False

            domain = scm_provider_data['domain'].strip()
            base_url = "https://api.github.com" if domain == "github.com" else "https://" + \
                domain + "/api/v3"
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))
            owner_or_org = scm_provider_data['owner_or_org'].strip()
            repo_full_name = f"{owner_or_org}/{repo_name}"

            pull_request_payload: dict[str,
                                       Any] = pull_request_config[scm_provider_type]

            head_ref = f"refs/heads/{
                repo.active_branch.name}"
            base_ref: str = pull_request_payload['base']

            if not base_ref.startswith("refs/heads/"):
                _logger.debug(
                    f"Updating base to 'refs/heads/{base_ref}'...")
                base_ref = f"refs/heads/{
                    base_ref}"

            pull_requests: PaginatedList = get_pull_requests_github(base_url=base_url,
                                                                    repo_full_name=repo_full_name,
                                                                    base=base_ref,
                                                                    head=head_ref,
                                                                    state="open",
                                                                    user_agent=app_config.USER_AGENT,
                                                                    auth=auth.Token(GITHUB_TOKEN))

            if pull_requests is not None:
                is_open_pr = pull_requests.totalCount > 0
                is_err = False

            else:
                is_open_pr = False
                is_err = True

            return is_open_pr, is_err

        else:
            _logger.error(f"Unsupported pull request type: '{
                          scm_provider_type}'")
            return False, True

    except KeyError as key_err:
        missing_key = str(key_err).strip().replace("'", "")
        path_to_key = missing_key
        if missing_key == 'type':
            path_to_key = f"targetRepos[].scmProvider.{missing_key}"
        elif missing_key == 'baseUrl':
            path_to_key = f"pullRequest.providerData.base_url"
        elif missing_key == 'project':
            path_to_key = f"pullRequest.providerData.{missing_key}"
        elif missing_key == scm_provider_type:
            path_to_key = f"pullRequest.{scm_provider_type}"
        elif missing_key == 'targetRefName':
            path_to_key = f"pullRequest.{scm_provider_type}.{missing_key}"
        targets_config_file_path = os.path.abspath(
            app_config.TARGETS_CONFIG_FILE)
        _logger.error(
            f"'{missing_key}' key not found. Please make sure to provide '{path_to_key}' in '{targets_config_file_path}'")
        _logger.info("Aborting..")
        return False, True

    except Exception as e:
        _logger.error(f"An unexpected error encountered: {str(e)}")
        return False, True


def raise_pull_request(repo: Repo, pull_request_config: dict[str, dict[str, Any]]) -> bool:
    """Raise a pull request based on the provided configuration.

    This function raises a pull request in the specified repository based on the provided configuration.
    It supports different source control management providers such as Azure DevOps and GitHub.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        pull_request_config (dict[str, dict[str, Any]]): The configuration for the pull request, containing 'providerData' and 'payload'.
            The 'providerData' key holds information about the source control management provider,
            and the 'payload' key contains data specific to the pull request.

    Returns:
        bool: True if the pull request is successfully raised, False otherwise.

    Raises:
        KeyError: If required keys are missing in the pull_request_config dictionary.
        Exception: If an unexpected error occurs during pull request creation.

    Note:
        The function handles pull request creation for different source control management providers.
        Ensure that the pull_request_config dictionary contains the necessary information for the desired provider.
        This function logs error messages using the configured logger.
    """
    try:
        pull_request: Union[GitPullRequest, PullRequest, None] = None
        scm_provider_data: dict[str, str] = repo.scm_provider
        scm_provider_type = scm_provider_data['type'].lower().strip()

        if scm_provider_type == "azuredevops":
            _logger.info("Azure DevOps pull request detected.")
            AZURE_DEVOPS_PAT = app_config.AZURE_DEVOPS_PAT

            if not AZURE_DEVOPS_PAT:
                _logger.error(
                    "Personal Access Token (PAT) not found. Please set 'AZURE_DEVOPS_PAT' environment variable with your Azure DevOps Personal Access Token (PAT) before running Code Migration Assistant")
                _logger.info("Aborting..")
                return False

            base_url = scm_provider_data['base_url'].strip()
            project = scm_provider_data['project'].strip()
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))

            pull_request_payload: dict[str,
                                       Any] = pull_request_config[scm_provider_type]

            pull_request_payload['description'] = "\n".join(
                pull_request_payload.get('description', []))
            pull_request_payload['sourceRefName'] = f"refs/heads/{
                repo.active_branch.name}"
            target_ref_name: str = pull_request_payload['targetRefName']

            if not target_ref_name.startswith("refs/heads/"):
                _logger.debug(
                    f"Updating targetRefName to 'refs/heads/{target_ref_name}'...")
                pull_request_payload['targetRefName'] = f"refs/heads/{
                    target_ref_name}"

            pull_request = raise_pull_request_azure_devops(base_url=base_url,
                                                           project=project,
                                                           repo_name=repo_name,
                                                           pull_request_payload=pull_request_payload,
                                                           user_agent=app_config.USER_AGENT,
                                                           creds=BasicAuthentication('PAT', AZURE_DEVOPS_PAT))
            return pull_request is not None

        elif scm_provider_type == "github":
            _logger.info("GitHub pull request detected.")
            GITHUB_TOKEN = app_config.GITHUB_TOKEN

            if not GITHUB_TOKEN:
                _logger.error(
                    "GitHub API Key not found. Please set 'GITHUB_TOKEN' environment variable with your GitHub Personal Access Token (PAT) before running Code Migration Assistant")
                _logger.info("Aborting..")
                return False

            domain = scm_provider_data['domain'].strip()
            base_url = "https://api.github.com" if domain == "github.com" else "https://" + \
                domain + "/api/v3"
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))
            owner_or_org = scm_provider_data['owner_or_org'].strip()
            repo_full_name = f"{owner_or_org}/{repo_name}"

            pull_request_payload: dict[str,
                                       Any] = pull_request_config[scm_provider_type]

            pull_request_payload['body'] = "\n".join(
                pull_request_payload.get('body', []))
            pull_request_payload['head'] = f"refs/heads/{
                repo.active_branch.name}"
            base_ref: str = pull_request_payload['base']

            if not base_ref.startswith("refs/heads/"):
                _logger.debug(
                    f"Updating base to 'refs/heads/{base_ref}'...")
                pull_request_payload['base'] = f"refs/heads/{
                    base_ref}"

            pull_request = raise_pull_request_github(base_url=base_url,
                                                     repo_full_name=repo_full_name,
                                                     pull_request_payload=pull_request_payload,
                                                     user_agent=app_config.USER_AGENT,
                                                     auth=auth.Token(GITHUB_TOKEN))

            return pull_request is not None

        else:
            _logger.error(f"Unsupported pull request type: '{
                          scm_provider_type}'")
            return False

    except KeyError as key_err:
        missing_key = str(key_err).strip().replace("'", "")
        path_to_key = missing_key
        if missing_key == 'type':
            path_to_key = f"targetRepos[].scmProvider.{missing_key}"
        elif missing_key == 'baseUrl':
            path_to_key = f"pullRequest.providerData.base_url"
        elif missing_key == 'project':
            path_to_key = f"pullRequest.providerData.{missing_key}"
        elif missing_key == scm_provider_type:
            path_to_key = f"pullRequest.{scm_provider_type}"
        elif missing_key == 'targetRefName':
            path_to_key = f"pullRequest.{scm_provider_type}.{missing_key}"
        targets_config_file_path = os.path.abspath(
            app_config.TARGETS_CONFIG_FILE)
        _logger.error(
            f"'{missing_key}' key not found. Please make sure to provide '{path_to_key}' in '{targets_config_file_path}'")
        _logger.info("Aborting..")
        return False

    except Exception as e:
        _logger.error(f"An unexpected error encountered: {str(e)}")
        return False


def get_files_count(repo: Repo, file_status: str = "unstaged") -> int:
    """
    Get the count of files based on their status in the repository.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        file_status (str, optional): The status of files to count. Valid options are 'staged', 'unstaged', or 'untracked'. Defaults to 'unstaged'.

    Returns:
        int: The count of files based on the specified status.
    """
    if file_status == "staged":
        return len(repo.index.diff("HEAD"))
    elif file_status == "modified":
        return len(repo.index.diff(None))
    elif file_status == "untracked":
        return len(repo.untracked_files)
    elif file_status == "unstaged":
        return len(repo.untracked_files) + len(repo.index.diff(None))
    else:
        raise ValueError(
            "Invalid file status. Must be 'staged', 'unstaged', or 'untracked'.")


def has_tracking_branch(branch: Head) -> bool:
    """Check if the branch has a tracking branch.

    Args:
        branch (Head): The branch to check.

    Returns:
        bool: True if the branch has a tracking branch, False otherwise.
    """
    return branch.tracking_branch() is not None


def needs_push(repo: Repo, branch_name: str | None = None) -> bool:
    """Check if the specified local branch or the active branch has commits that need to be pushed to its tracking remote branch.

    Args:
        repo (Repo): The GitPython Repo object representing the local repository.
        branch_name (str, optional): The name of the local branch. If not provided, the active branch is used.

    Returns:
        bool: True if there are commits to be pushed, False otherwise.
    """
    branch = repo.heads[branch_name] if branch_name else repo.active_branch

    tracking_branch = branch.tracking_branch()
    if tracking_branch:
        return any(repo.iter_commits(f"{tracking_branch.name}..{branch.name}"))
    return False
