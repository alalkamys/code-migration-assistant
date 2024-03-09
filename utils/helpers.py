from config import app_config

from typing import Any
import json
import logging
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
