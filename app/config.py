from app.utils.filters import MaxLevelFilter
from app.utils.formatters import ColoredFormatter

from git import RemoteProgress
from logging import Logger
import logging
import os


class AppConfig:
    """Configuration class for the Code Migration Assistant application.

    Attributes:
        APP_NAME (str): The name of the application. Defaults to "code_migration_assistant".
        APP_MODES (dict): Available modes for the application and their corresponding flags configuration.
            The flags configuration is a nested dictionary with boolean values indicating whether each flag is enabled or not.
            Keys are mode names ('dev', 'prod', etc.), and values are dictionaries with flag names as keys and boolean values as values.
        LOG_LEVEL (str): The logging level for the application. Defaults to "INFO".
        TARGETS_CONFIG_FILE (str): The file path to the targets configuration file. Defaults to "./config.json".
        REMOTE_TARGETS_CLONING_PATH (str): The path where remote targets are cloned. Defaults to "./remote-targets".
        AZURE_DEVOPS_PAT (str): The Personal Access Token (PAT) for Azure DevOps. Defaults to None.
        GITHUB_TOKEN (str): The Personal Access Token (PAT) for GitHub. Defaults to None.
        GITHUB_ENTERPRISE_TOKEN (str): The Personal Access Token (PAT) for GitHub Enterprise. Defaults to None.
        ACTOR (dict): A dictionary containing the username and email of the application's agent. Defaults to {'username': "Code Migration Assistant Agent", 'email': "code_migration_assistant_agent@gmail.com"}
        USER_AGENT (str): The user agent for making HTTP requests. Defaults to "alalkamys/code-migration-assistant".
        LOGGING_CONFIG (dict): Configuration settings for logging.
    """
    APP_NAME = os.getenv('CODE_MIGRATION_ASSISTANT_APP_NAME',
                         "code_migration_assistant")

    APP_MODES: dict[str, dict[str, dict[str, bool]]] = {
        'dev': {
            'flags': {
                'check_branch': False,
                'setup_identity': False,
                'search_only': True,
                'commit': False,
                'push': False,
                'create_pull_request': False
            }
        },
        'prod': {
            'flags': {
                'check_branch': True,
                'setup_identity': True,
                'search_only': False,
                'commit': True,
                'push': True,
                'create_pull_request': True
            }
        }
    }

    LOG_LEVEL = os.getenv('CODE_MIGRATION_ASSISTANT_LOG_LEVEL', "INFO")

    TARGETS_CONFIG_FILE = os.getenv(
        'CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE', "./config.json")

    REMOTE_TARGETS_CLONING_PATH = os.getenv(
        'CODE_MIGRATION_ASSISTANT_REMOTE_TARGETS_CLONING_PATH', "./remote-targets")

    AZURE_DEVOPS_PAT = os.getenv('AZURE_DEVOPS_PAT', None)

    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)

    GITHUB_ENTERPRISE_TOKEN = os.getenv('GITHUB_ENTERPRISE_TOKEN', None)

    ACTOR = {
        'username': os.getenv('CODE_MIGRATION_ASSISTANT_ACTOR_USERNAME', "Code Migration Assistant Agent"),
        'email': os.getenv('CODE_MIGRATION_ASSISTANT_ACTOR_EMAIL', "code_migration_assistant_agent@gmail.com")
    }

    USER_AGENT = os.getenv(
        'CODE_MIGRATION_ASSISTANT_USER_AGENT', "alalkamys/code-migration-assistant")

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': True,
        'filters': {
            'upper_threshold_filter': {
                '()': MaxLevelFilter,
                'maxlevel': logging.WARNING,
                'invert': False
            },
            'upper_threshold_inverter': {
                '()': MaxLevelFilter,
                'maxlevel': logging.WARNING,
                'invert': True
            }
        },
        'formatters': {
            'colored_formatter': {
                '()': ColoredFormatter,
                'fmt': '[%(levelname)s]:%(name)s:%(asctime)s, %(message)s'
            }
        },
        'handlers': {
            'stdout_handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored_formatter',
                'stream': 'ext://sys.stdout',
                'filters': ['upper_threshold_filter']
            },
            'stderr_handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored_formatter',
                'stream': 'ext://sys.stderr',
                'filters': ['upper_threshold_inverter']
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
