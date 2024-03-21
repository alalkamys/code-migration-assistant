from app.config import app_config
from app.helpers.git import checkout_branch
from app.helpers.git import commit_changes
from app.helpers.git import get_files_count
from app.helpers.git import has_tracking_branch
from app.helpers.git import identity_setup
from app.helpers.git import needs_push
from app.helpers.git import push_changes
from app.helpers.operations import load_targets_config
from app.helpers.operations import load_target_repos
from app.helpers.operations import search_and_replace
from app.helpers.scm_providers_operations import is_open_pull_requests
from app.helpers.scm_providers_operations import raise_pull_request

from copy import deepcopy
from tabulate import tabulate
from typing import Literal
import logging.config
import os
import sys

if __name__ == "__main__":
    logging.config.dictConfig(app_config.LOGGING_CONFIG)

    _logger = logging.getLogger(app_config.APP_NAME)

    TARGETS_CONFIG = load_targets_config(
        file_path=app_config.TARGETS_CONFIG_FILE)
    TARGET_REPOS = load_target_repos(repos=TARGETS_CONFIG['targetRepos'])
    TARGET_BRANCH = TARGETS_CONFIG['targetBranch']
    REPLACEMENTS = TARGETS_CONFIG['replacements']
    FILES_TO_EXCLUDE = TARGETS_CONFIG.get('filesToExclude', [])

    MODE: Literal['dev', 'prod'] = TARGETS_CONFIG.get(
        'mode', 'prod').strip().lower()

    if MODE not in app_config.APP_MODES:
        _logger.error(f"Invalid mode: '{
                      MODE}'. The mode must be set to either 'dev' for development/testing or 'prod' for production usage.")
        _logger.info("Exiting..")
        sys.exit(6)

    if len(TARGET_REPOS) > 0 and len(REPLACEMENTS) > 0:
        _logger.info(f"Loaded '{len(TARGET_REPOS)}' repositories out of '{
            len(TARGETS_CONFIG['targetRepos'])}' provided repositories")
        _logger.info(f"'{len(TARGET_REPOS)}' target repo(s) found")
        _logger.info("Initiating code migration assistant program..")
        _logger.info(f"Mode: {MODE}")
        final_result = {}
        for repo in TARGET_REPOS:
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))

            _logger.info(f"Migrating '{repo_name}'..")

            check_branch = app_config.APP_MODES[MODE]['flags']['check_branch']
            setup_identity = app_config.APP_MODES[MODE]['flags']['setup_identity']
            search_only = app_config.APP_MODES[MODE]['flags']['search_only']
            commit = app_config.APP_MODES[MODE]['flags']['commit']
            push = app_config.APP_MODES[MODE]['flags']['push']
            create_pull_request = app_config.APP_MODES[MODE]['flags']['create_pull_request']

            _logger.debug("Initial Flags")
            _logger.debug("-------------")
            _logger.debug(f"check_branch: {check_branch}")
            _logger.debug(f"setup_identity: {setup_identity}")
            _logger.debug(f"search_only: {search_only}")
            _logger.debug(f"commit: {commit}")
            _logger.debug(f"push: {push}")
            _logger.debug(f"create_pull_request: {create_pull_request}")

            if setup_identity:
                identity_configured = identity_setup(
                    repo=repo, actor_username=app_config.ACTOR['username'], actor_email=app_config.ACTOR['email'])

                if not identity_configured:
                    _logger.error(
                        f"Failed to setup the identity for '{repo_name}'. Review the logs for more details")
                    if repo != TARGET_REPOS[-1]:
                        _logger.info("Skipping to the next migration..")
                        continue
                    _logger.info("Exiting..")
                    sys.exit(2)

            if check_branch:
                branch_checked = checkout_branch(
                    repo=repo, branch_name=TARGET_BRANCH['name'], from_branch=TARGET_BRANCH.get('from', None))

                if not branch_checked:
                    _logger.error(
                        f"'{TARGET_BRANCH['name']}' checking failed. Review the logs for more details")
                    if repo != TARGET_REPOS[-1]:
                        _logger.info("Skipping to the next migration..")
                        continue
                    _logger.info("Exiting..")
                    sys.exit(3)

            result = search_and_replace(
                directory=repo.working_tree_dir, patterns=REPLACEMENTS, excluded_files=FILES_TO_EXCLUDE, search_only=search_only)

            if not result:
                _logger.error(
                    "Migration error. Review the logs for more details")
                if repo != TARGET_REPOS[-1]:
                    _logger.info("Skipping to the next migration..")
                    continue
                _logger.info("Exiting..")
                sys.exit(10)

            match_count_total = sum([result[pattern]['count']
                                    for pattern in result.keys()])

            _logger.info(f"'{repo_name}' has a total of '{
                match_count_total}' patterns matching")

            final_result[repo_name] = result

            if MODE != 'dev':

                PULL_REQUEST = deepcopy(
                    TARGETS_CONFIG.get('pullRequest', None))

                if match_count_total == 0:
                    _logger.info(
                        "Checking if there are modified/staged files by a previous run..")
                    modified_files_count = get_files_count(
                        repo=repo, file_status="modified")
                    staged_files_count = get_files_count(
                        repo=repo, file_status="staged")
                    _logger.debug(f"Modified Files Count: '{
                        modified_files_count}'")
                    _logger.debug(f"Staged Files Count: '{
                                  staged_files_count}'")
                    if modified_files_count + staged_files_count > 0:
                        _logger.info("Modified/staged files detected")
                        _logger.info("Proceeding with committing changes..")
                    else:
                        _logger.info("All files are tracked")
                        commit = False
                        _logger.info(
                            "Checking if current branch has an upstream branch..")
                        if has_tracking_branch(repo.active_branch):
                            _logger.info(
                                f"'{repo.active_branch.name}' has an upstream branch")
                            _logger.info(
                                "Checking if upstream branch is up-to-date with the current branch..")
                            if needs_push(repo=repo):
                                _logger.info(
                                    "Upstream branch is outdated. Requires pushing")
                                _logger.info("Proceeding with pushing..")
                            else:
                                _logger.info("Upstream is up-to-date")
                                push = False
                                if PULL_REQUEST:
                                    _logger.info(
                                        "Checking if there is an open pull request..")
                                    open_pull_request, error = is_open_pull_requests(
                                        repo=repo, pull_request_config=PULL_REQUEST)

                                    if error:
                                        _logger.error(f"Querying '{
                                            repo_name}' open requests failed. Review the logs for more details")
                                        if repo != TARGET_REPOS[-1]:
                                            _logger.info(
                                                "Skipping to the next migration..")
                                            continue
                                        _logger.info("Exiting..")
                                        sys.exit(6)

                                    if open_pull_request:
                                        _logger.info(
                                            f"'{repo_name}' has an open pull request. Skipping..")
                                        create_pull_request = False
                                        if repo != TARGET_REPOS[-1]:
                                            _logger.info(
                                                "Skipping to the next migration..")
                                        continue
                                    else:
                                        _logger.info(
                                            f"'{repo_name}' doesn't have an open pull request")
                                        _logger.info(
                                            "Proceeding with raising pull request..")

                                else:
                                    if repo != TARGET_REPOS[-1]:
                                        _logger.info(
                                            "Skipping to the next migration..")
                                    continue
                        else:
                            _logger.info(
                                f"'{repo.active_branch}' doesn't have an upstream branch")
                            if repo != TARGET_REPOS[-1]:
                                _logger.info(
                                    "Skipping to the next migration..")
                            continue

            _logger.debug("Flags After Checks")
            _logger.debug("------------------")
            _logger.debug(f"check_branch: {check_branch}")
            _logger.debug(f"setup_identity: {setup_identity}")
            _logger.debug(f"search_only: {search_only}")
            _logger.debug(f"commit: {commit}")
            _logger.debug(f"push: {push}")
            _logger.debug(f"create_pull_request: {create_pull_request}")

            if commit:
                COMMIT_MESSAGE = TARGETS_CONFIG.get('commitMessage', None)
                COMMIT_TITLE = COMMIT_MESSAGE.get(
                    'title', "feat: code migration") if COMMIT_MESSAGE else "feat: code migration"
                COMMIT_DESCRIPTION = COMMIT_MESSAGE.get(
                    'description', None) if COMMIT_MESSAGE else None

                commit_changes(repo=repo, title=COMMIT_TITLE, description="\n".join(
                    COMMIT_DESCRIPTION) if COMMIT_DESCRIPTION else COMMIT_DESCRIPTION, auto_stage=True)

            if push:
                changes_pushed = push_changes(repo=repo)

                if not changes_pushed:
                    _logger.error(
                        f"'{repo_name}' remote push process failed. Review the logs for more details")
                    if repo != TARGET_REPOS[-1]:
                        _logger.info("Skipping to the next migration..")
                        continue
                    _logger.info("Exiting..")
                    sys.exit(4)

            if create_pull_request:
                if not PULL_REQUEST:
                    _logger.info(f"No pull request data configured for '{
                        repo_name}'. Skipping..")
                    continue

                pull_request_raised = raise_pull_request(
                    repo=repo, pull_request_config=PULL_REQUEST)

                if not pull_request_raised:
                    _logger.error(
                        f"'{repo_name}' pull request raising failed. Review the logs for more details")
                    if repo != TARGET_REPOS[-1]:
                        _logger.info("Skipping to the next migration..")
                        continue
                    _logger.info("Exiting..")
                    sys.exit(5)

        combined_table = []
        for repo_name, repo_result in final_result.items():
            for pattern, pattern_data in repo_result.items():
                if pattern_data["count"] == 0:
                    matched_files_text = "N/A"
                else:
                    matched_files_table = []
                    for file_path, match_count in pattern_data["match"].items():
                        matched_files_table.append([file_path, match_count])
                    matched_files_text = tabulate(
                        matched_files_table, headers=["Matched File", "Match Count"], tablefmt="grid")
                row = [repo_name, pattern,
                       pattern_data["count"], matched_files_text]
                combined_table.append(row)

        headers = ["Repository", "Pattern", "Count", "Matched Files"]
        _logger.info("Migration summary results:")
        _logger.info(
            f"\n{tabulate(combined_table, headers=headers, tablefmt="grid")}")
    else:
        _logger.info("No targets to migrate detected or replacements found")
        _logger.info("Nothing to do")
        _logger.info("Exiting..")
        sys.exit(0)
