from config import app_config

from git import Repo
from git.exc import GitCommandError
from git.exc import NoSuchPathError
from typing import Any
from typing import List
from typing import Type
import json
import logging
import os
import sys

_logger = logging.getLogger(app_config.APP_NAME)


def load_targets_configs(file_path: str) -> dict[str, Any]:
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
    sys.exit(1)


def load_target_repos(repos: List[dict]) -> List[Repo]:
    result = []
    for repo in repos:
        try:
            result.append(Repo(path=repo['source']) if repo['type'].lower() == "local" else Repo.clone_from(
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


def identity_setup(repo: Type[Repo], actor_username: str, actor_email: str) -> None:
    config_writer = repo.config_writer()
    _logger.debug(f"Setting username to {actor_username}")
    config_writer.set_value('user', 'name', actor_username).release()
    _logger.debug(f"Setting email to <{actor_email}>")
    config_writer.set_value('user', 'email', actor_email).release()
    del (config_writer)
