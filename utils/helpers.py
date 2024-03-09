from config import app_config

from git import Repo
from git.remote import PushInfoList
from git.exc import GitCommandError
from git.exc import NoSuchPathError
from typing import Any
from typing import List
from typing import Type
import json
import logging
import os
import re
import sys

_logger = logging.getLogger(app_config.APP_NAME)


def load_targets_config(file_path: str) -> dict[str, Any]:
    try:
        with open(file_path) as f:
            _logger.info(f"Loading '{file_path}'")
            return json.load(f)
    except FileNotFoundError:
        error_message = f"Configuration file '{
            file_path}' not found."
    except json.JSONDecodeError:
        error_message = f"Unable to load configuration from '{
            file_path}'. Invalid JSON format."
    _logger.error(error_message)
    _logger.info("Exiting..")
    sys.exit(1)


def load_target_repos(repos: List[dict]) -> List[Repo]:
    result = []
    for repo in repos:
        try:
            result.append(Repo(path=repo['source']) if repo['type'].strip().lower() == "local" else Repo.clone_from(
                url=repo['source'], to_path=f"{app_config.REMOTE_TARGETS_CLONING_PATH}/{repo['name']}"))
        except GitCommandError as git_cmd_err:
            if git_cmd_err.status == 128 and 'already exists' in git_cmd_err.stderr:
                cwd = os.getcwd()
                repo_absolute_path = os.path.abspath(os.path.join(
                    cwd, f"{app_config.REMOTE_TARGETS_CLONING_PATH}/{repo['name']}"))
                _logger.info(f"'{repo_absolute_path}' already exists, using..")
                result.append(
                    Repo(path=f"{app_config.REMOTE_TARGETS_CLONING_PATH}/{repo['name']}"))
            else:
                _logger.error(f"Unexpected GitCommandError: {
                              str(git_cmd_err)}")
        except NoSuchPathError:
            _logger.error(f"Invalid 'Remote' repo URL '{
                          repo['source']}' no such path. Check '{repo['name']}' source URL")
        except Exception as e:
            _logger.error(f"Unexpected error when loading '{
                          repo['name']}': {str(e)}")
    return result


# TODO: improve the error handling
def identity_setup(repo: Type[Repo], actor_username: str, actor_email: str) -> None:
    config_writer = repo.config_writer()
    _logger.debug(f"Setting username to {actor_username}")
    config_writer.set_value('user', 'name', actor_username).release()
    _logger.debug(f"Setting email to <{actor_email}>")
    config_writer.set_value('user', 'email', actor_email).release()
    del (config_writer)


# TODO: improve the error handling
def checkout_branch(branch_name: str, repo: Type[Repo]) -> None:
    _logger.info(f"Requested target branch: '{
        branch_name}', checking if exists..")
    if branch_name in [ref.name for ref in repo.references]:
        _logger.info(f"'{branch_name}' already exists, switching..")
        repo.git.checkout(branch_name)
    else:
        _logger.info(f"'{branch_name}' doesn't exist, creating..")
        repo.git.checkout('-b', branch_name)


def search_and_replace(directory: str, patterns: dict, excluded_files: list[str] = [], hidden_dirs: bool = False) -> dict[str, dict[str, Any]] | None:
    """Search all files in a directory (including subdirectories) for patterns and replace them, and returns the number of matching for each given pattern."""
    result = {pattern: {'count': 0, 'match': {}}
              for pattern in patterns.keys()}
    if hidden_dirs:
        _logger("Including hidden directories in the search")
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


# TODO: improve the error handling
def commit_changes(repo: Type[Repo], title: str, description: str = None, stage_all: bool = False) -> None:
    OPTION = '-am' if stage_all else '-m'
    _logger.info("Committing changes..")
    repo.git.commit(OPTION, title, '-m',
                    description) if description else repo.git.commit(OPTION, title)


def push_changes(repo: Type[Repo], target_remote: str = None, target_branch: str = None) -> Type[PushInfoList] | None:
    if not target_remote:
        _logger.info("No target remote was provided. Will use 'origin'..")
        target_remote = 'origin'
    if repo.remotes[target_remote].exists():
        _logger.info(f"Pushing changes to '{target_remote}'..")
        remote = repo.remotes[target_remote]
        remote.push(f"{repo.head.name}:{
                    target_branch if target_branch else repo.active_branch.name}")[0]
    else:
        _logger.warn(
            f"'{target_remote}' remote doesn't exist, checking configured remotes..")
        if len(repo.remotes) == 0:
            _logger.info(
                "No remotes were found. Make sure to configure the remote")
            _logger.info("Aborting pushing..")
            return None
        _logger.info("Remote detected, using..")
        remote = repo.remotes[0]
        _logger.info(f"Pushing changes to '{remote.name}'..")
        return remote.push()[0]
