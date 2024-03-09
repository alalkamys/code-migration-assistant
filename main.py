from config import app_config
from utils.helpers import load_targets_configs
from utils.helpers import load_target_repos

import logging.config

if __name__ == "__main__":
    logging.config.dictConfig(app_config.LOGGING_CONFIG)

    _logger = logging.getLogger(app_config.APP_NAME)

    _logger.info("Initiating code migration assistant program..")

    TARGETS_CONFIG = load_targets_configs(
        file_path=app_config.TARGETS_CONFIG_FILE)
    TARGET_REPOS = load_target_repos(repos=TARGETS_CONFIG['targetRepos'])

    _logger.info([repo.working_dir for repo in TARGET_REPOS])
