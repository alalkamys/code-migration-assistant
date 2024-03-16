from app.config import app_config

from azure.devops.connection import Connection
from azure.devops.credentials import BasicAuthentication
from azure.devops.exceptions import AzureDevOpsAuthenticationError
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_0.git import GitPullRequest
from azure.devops.v7_0.git import GitRepository
from azure.devops.v7_0.git.git_client import GitClient
from azure.devops.v7_0.git.models import GitPullRequestSearchCriteria
from msrest.exceptions import ClientRequestError
from typing import Any
from typing import List
from typing import Union
from urllib import parse
import logging

_logger = logging.getLogger(app_config.APP_NAME)


def get_pull_requests(
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
        user_agent (str): The user agent for making HTTP requests.
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


def create_pull_request(
    base_url: str,
    project: str,
    repo_name: str,
    pull_request_payload: dict[str, Any],
    user_agent: str,
    creds: BasicAuthentication
) -> GitPullRequest | None:
    """Creates a pull request in Azure DevOps.

    Args:
        base_url (str): The base URL of the Azure DevOps service.
        project (str): The name of the project in which the repository resides.
        repo_name (str): The name of the repository for which the pull request is raised.
        pull_request_payload (dict[str, Any]): The payload containing the details of the pull request.
        creds (BasicAuthentication): The authentication credentials for Azure DevOps.
        user_agent (str): The user agent for making HTTP requests.

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
