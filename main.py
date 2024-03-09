from config import app_config
from utils.helpers import checkout_branch
from utils.helpers import identity_setup
from utils.helpers import load_targets_config
from utils.helpers import load_target_repos
from utils.helpers import search_and_replace

import json
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

    if len(TARGET_REPOS) > 0 and len(REPLACEMENTS) > 0:
        _logger.info(f"{len(TARGET_REPOS)} target repo(s) found")
        _logger.info("Initiating code migration assistant program..")
        final_result = {}
        for repo in TARGET_REPOS:
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))

            _logger.info(f"Migrating '{repo_name}'..")

            identity_setup(
                repo=repo, actor_username=app_config.ACTOR['username'], actor_email=app_config.ACTOR['email'])

            checkout_branch(repo=repo, branch_name=TARGET_BRANCH)

            result = search_and_replace(
                directory=repo.working_tree_dir, patterns=REPLACEMENTS)

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

        _logger.info(f"Migration summary results: {
            json.dumps(final_result, sort_keys=True, indent=4)}")
    else:
        _logger.info("No targets to migrate detected or replacements found")
        _logger.info("Nothing to do")
        _logger.info("Exiting..")
        sys.exit(0)
