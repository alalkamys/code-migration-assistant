from config import app_config

import logging.config

if __name__ == "__main__":
    logging.config.dictConfig(app_config.LOGGING_CONFIG)

    _logger = logging.getLogger(app_config.APP_NAME)
    
    _logger.info("Initiating code migration assistant program..")