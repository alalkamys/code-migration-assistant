from utils import filters

from git import RemoteProgress
from logging import Logger
import logging
import os


class AppConfig:
    APP_NAME = os.getenv('CODE_MIGRATION_ASSISTANT_APP_NAME',
                         "code_migration_assistant")

    LOG_LEVEL = os.getenv('CODE_MIGRATION_ASSISTANT_LOG_LEVEL', "INFO")

    TARGETS_CONFIG_FILE = os.getenv(
        'CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE', "./config.json")

    REMOTE_TARGETS_CLONING_PATH = os.getenv(
        'CODE_MIGRATION_ASSISTANT_REMOTE_TARGETS_CLONING_PATH', "./remote-targets")

    AZURE_DEVOPS_PAT = os.getenv('AZURE_DEVOPS_PAT', None)

    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)

    ACTOR = {
        'username': "Code Migration Assistant Agent",
        'email': 'code_migration_assistant_agent@gmail.com'
    }

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': True,
        'filters': {
            'info_lvl_filter': {
                '()': filters.SingleLevelFilter,
                'passlevel': logging.INFO,
                'reject': False
            },
            'info_lvl_filter_inverter': {
                '()': filters.SingleLevelFilter,
                'passlevel': logging.INFO,
                'reject': True
            }
        },
        'formatters': {
            'default': {
                'format': '[%(levelname)s]:%(name)s:%(asctime)s, %(message)s',
            }
        },
        'handlers': {
            'stdout_handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
                'filters': ['info_lvl_filter']
            },
            'stderr_handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'stream': 'ext://sys.stderr',
                'filters': ['info_lvl_filter_inverter']
            },
        },
        'loggers': {
            APP_NAME: {
                'handlers': ['stdout_handler', 'stderr_handler'],
                'level': LOG_LEVEL,
                'propagate': False,
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['stdout_handler', 'stderr_handler'],
        }
    }


class RemoteProgressReporter(RemoteProgress):
    def __init__(self, logger: Logger) -> None:
        super().__init__()
        self._logger = logger

    def update(self, op_code, cur_count, max_count=None, message=""):
        self._logger.debug(f"{op_code} {cur_count} {max_count} {
            cur_count / (max_count or 100.0)} {message or "NO MESSAGE"}")


app_config = AppConfig
