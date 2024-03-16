import logging


class ColoredFormatter(logging.Formatter):
    """
    Formatter for colored logging messages.

    This formatter applies color codes to different log levels for enhanced readability.
    It is adapted from https://stackoverflow.com/a/56944256/3638629.

    Attributes:
        BLACK (str): Color code for black.
        RED (str): Color code for red.
        GREEN (str): Color code for green.
        YELLOW (str): Color code for yellow.
        BLUE (str): Color code for blue.
        PURPLE (str): Color code for purple.
        CYAN (str): Color code for cyan.
        GREY (str): Color code for grey.
        DARK_GREY (str): Color code for dark grey.
        LIGHT_RED (str): Color code for light red.
        LIGHT_GREEN (str): Color code for light green.
        LIGHT_YELLOW (str): Color code for light yellow.
        LIGHT_BLUE (str): Color code for light blue.
        LIGHT_PURPLE (str): Color code for light purple.
        LIGHT_CYAN (str): Color code for light cyan.
        WHITE (str): Color code for white.
        RESET (str): Reset color code.

    Methods:
        __init__(fmt): Initialize the formatter with the specified format.
        format(record): Format the log record with the appropriate color based on its level.

    """

    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREY = '\033[0;37m'

    DARK_GREY = '\033[1;30m'
    LIGHT_RED = '\033[1;31m'
    LIGHT_GREEN = '\033[1;32m'
    LIGHT_YELLOW = '\033[1;33m'
    LIGHT_BLUE = '\033[1;34m'
    LIGHT_PURPLE = '\033[1;35m'
    LIGHT_CYAN = '\033[1;36m'
    WHITE = '\033[1;37m'

    RESET = "\033[0m"

    def __init__(self, fmt):
        """
        Initialize the ColoredFormatter instance.

        Args:
            fmt (str): The log message format.

        """
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.LIGHT_PURPLE + self.fmt + self.RESET,
            logging.INFO: self.RESET + self.fmt + self.RESET,
            logging.WARNING: self.LIGHT_YELLOW + self.fmt + self.RESET,
            logging.ERROR: self.LIGHT_RED + self.fmt + self.RESET,
            logging.CRITICAL: self.RED + self.fmt + self.RESET
        }

    def format(self, record):
        """
        Format the log record with the appropriate color based on its level.

        Args:
            record: The log record to format.

        Returns:
            str: The formatted log message with color.

        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
