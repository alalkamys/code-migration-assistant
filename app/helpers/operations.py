from app.config import app_config

from git import Repo
from git.exc import GitCommandError
from git.exc import NoSuchPathError
from typing import Any
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


# TODO: find a way to determine if the end result contains some errors but were skipped
def search_and_replace(directory: str, patterns: dict, excluded_files: list[str] = [], hidden_dirs: bool = False, search_only: bool = False) -> dict[str, dict[str, Any]] | None:
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
                if updated_content != content and not search_only:
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
