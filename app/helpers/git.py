from app.config import app_config
from app.config import RemoteProgressReporter

from git import Actor
from git import Repo
from git.refs.head import Head
from git.remote import PushInfo
from git.remote import PushInfoList
from git.exc import GitCommandError
from git.exc import NoSuchPathError
from typing import Any
import json
import logging
import os
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