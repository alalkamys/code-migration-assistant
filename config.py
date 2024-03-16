from utils import filters

from git import RemoteProgress
from logging import Logger
import logging
import os


class AppConfig:
    """Configuration class for the Code Migration Assistant application.

    Attributes:
        APP_NAME (str): The name of the application. Defaults to "code_migration_assistant".
        LOG_LEVEL (str): The logging level for the application. Defaults to "INFO".
        TARGETS_CONFIG_FILE (str): The file path to the targets configuration file. Defaults to "./config.json".
        REMOTE_TARGETS_CLONING_PATH (str): The path where remote targets are cloned. Defaults to "./remote-targets".
        AZURE_DEVOPS_PAT (str): The Personal Access Token (PAT) for Azure DevOps. Defaults to None.
        GITHUB_TOKEN (str): The Personal Access Token (PAT) for GitHub. Defaults to None.
        GITHUB_ENTERPRISE_TOKEN (str): The Personal Access Token (PAT) for GitHub Enterprise. Defaults to None.
        ACTOR (dict): A dictionary containing the username and email of the application's agent.
        USER_AGENT (str): The user agent for making HTTP requests. Defaults to "alalkamys/code-migration-assistant".
        LOGGING_CONFIG (dict): Configuration settings for logging.
    """
    APP_NAME = os.getenv('CODE_MIGRATION_ASSISTANT_APP_NAME',
                         "code_migration_assistant")

    LOG_LEVEL = os.getenv('CODE_MIGRATION_ASSISTANT_LOG_LEVEL', "INFO")

    TARGETS_CONFIG_FILE = os.getenv(
        'CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE', "./config.json")

    REMOTE_TARGETS_CLONING_PATH = os.getenv(
        'CODE_MIGRATION_ASSISTANT_REMOTE_TARGETS_CLONING_PATH', "./remote-targets")

    AZURE_DEVOPS_PAT = os.getenv('AZURE_DEVOPS_PAT', None)

    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)
    
    GITHUB_ENTERPRISE_TOKEN = os.getenv('GITHUB_ENTERPRISE_TOKEN', None)

    ACTOR = {
        'username': "Code Migration Assistant Agent",
        'email': 'code_migration_assistant_agent@gmail.com'
    }

    USER_AGENT = os.getenv(
        'CODE_MIGRATION_ASSISTANT_USER_AGENT', "alalkamys/code-migration-assistant")

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
        """Initialize the RemoteProgressReporter.

        Args:
            logger (Logger): The logger object to log the progress updates.
        """
        super().__init__()
        self._logger = logger

    def update(self, op_code, cur_count, max_count=None, message=""):
        """Update method to report progress.

        Args:
            op_code: The operation code.
            cur_count: The current count.
            max_count: The maximum count.
            message: The progress message.
        """
        self._logger.debug(f"{op_code} {cur_count} {max_count} {
            cur_count / (max_count or 100.0)} {message or "NO MESSAGE"}")


app_config = AppConfig
