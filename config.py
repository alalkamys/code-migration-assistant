from utils import filters

import logging
import os


class AppConfig:
    APP_NAME = os.getenv('CODE_MIGRATION_ASSISTANT_APP_NAME',
                         "code_migration_assistant")

    TARGETS_CONFIG_FILE = os.getenv(
        'CODE_MIGRATION_ASSISTANT_TARGETS_CONFIG_FILE', "./config.json")

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
                'level': 'INFO',
                'propagate': False,
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['stdout_handler', 'stderr_handler'],
        }
    }


app_config = AppConfig
