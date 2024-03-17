from app.config import app_config
from app.helpers import azuredevops
from app.helpers import github

from azure.devops.credentials import BasicAuthentication
from azure.devops.v7_0.git import GitPullRequest
from git import Repo
from github import Auth as auth
from github.PaginatedList import PaginatedList
from github.PullRequest import PullRequest
from typing import Any
from typing import Union
import logging
import os

_logger = logging.getLogger(app_config.APP_NAME)


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

            pull_requests = azuredevops.get_pull_requests(base_url=base_url,
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

            pull_requests: PaginatedList = github.get_pulls(base_url=base_url,
                                                            repo_full_name=repo_full_name,
                                                            base=base_ref,
                                                            head=head_ref,
                                                            state="open",
                                                            user_agent=app_config.USER_AGENT,
                                                            auth=auth.Token(GITHUB_TOKEN))

            if pull_requests is not None:
                is_open_pr = pull_requests.totalCount > 0
                is_err = False
                _logger.debug(f"Received pulls total count: '{
                              pull_requests.totalCount}'")
            else:
                is_open_pr = False
                is_err = True

            _logger.debug(f"is_open_pr: '{is_open_pr}'")
            _logger.debug(f"is_err: '{is_err}'")
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

            pull_request = azuredevops.create_pull_request(base_url=base_url,
                                                           project=project,
                                                           repo_name=repo_name,
                                                           pull_request_payload=pull_request_payload,
                                                           user_agent=app_config.USER_AGENT,
                                                           creds=BasicAuthentication('PAT', AZURE_DEVOPS_PAT))
            return pull_request is not None

        elif scm_provider_type == "github":
            _logger.info("GitHub pull request detected.")

            domain = scm_provider_data['domain'].strip()

            GITHUB_TOKEN = app_config.GITHUB_TOKEN if domain == "github.com" else app_config.GITHUB_ENTERPRISE_TOKEN

            if not GITHUB_TOKEN:
                _logger.error(
                    "GitHub API Key not found. Please set 'GITHUB_TOKEN' environment variable for with your GitHub Personal Access Token (PAT) or set 'GITHUB_ENTERPRISE_TOKEN' for GitHub Enterprise before running Code Migration Assistant")
                _logger.info("Aborting..")
                return False

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

            pull_request = github.create_pulls(base_url=base_url,
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
