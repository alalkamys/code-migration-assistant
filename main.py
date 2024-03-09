from config import app_config
from utils.helpers import checkout_branch
from utils.helpers import identity_setup
from utils.helpers import load_targets_config
from utils.helpers import load_target_repos

import logging.config
import os

if __name__ == "__main__":
    logging.config.dictConfig(app_config.LOGGING_CONFIG)

    _logger = logging.getLogger(app_config.APP_NAME)

    TARGETS_CONFIG = load_targets_config(
        file_path=app_config.TARGETS_CONFIG_FILE)
    TARGET_REPOS = load_target_repos(repos=TARGETS_CONFIG['targetRepos'])
    TARGET_BRANCH = TARGETS_CONFIG['targetBranch']

    if len(TARGET_REPOS) > 0:
        _logger.info(f"{len(TARGET_REPOS)} target repo(s) found")
        _logger.info("Initiating code migration assistant program..")

        for repo in TARGET_REPOS:
            repo_name = os.path.basename(
                os.path.normpath(repo.working_tree_dir))

            _logger.info(f"Migrating '{repo_name}'..")

            identity_setup(
                repo=repo, actor_username=app_config.ACTOR['username'], actor_email=app_config.ACTOR['email'])

            checkout_branch(repo=repo, branch_name=TARGET_BRANCH)
