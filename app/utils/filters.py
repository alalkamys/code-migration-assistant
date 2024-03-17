from logging import LogRecord

import logging


class SingleLevelFilter(logging.Filter):
    """
    A class to represent a single logging level filter.

    ...

    Attributes
    ----------
    passlevel : int
        log level to pass
    reject : bool
        whether to reject self.passlevel 

    Methods
    -------
    filter(record):
        compares incoming logging records level no and either filter them to self.passlevel only and if self.reject=True it will reject those with 
        same self.passlevel.
    """

    def __init__(self, passlevel: int, reject: bool):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record: LogRecord):
        """Filters incoming logging record.

        Returns:
            compares incoming logging records level no and either filter them to self.passlevel only and if self.reject=True it will reject those with 
            same self.passlevel.
        """
        if self.reject:
            return (record.levelno != self.passlevel)
        else:
            return (record.levelno == self.passlevel)


class MaxLevelFilter(logging.Filter):
    """
    A filter to control logging levels.

    Attributes:
        maxlevel (int): The maximum log level to allow (inclusive).
        invert (bool): If True, invert the filter logic.

    Methods:
        filter(record): Apply the filter to the given record.
    """

    def __init__(self, maxlevel: int, invert: bool = False):
        """
        Initialize the MaxLevelFilter.

        Args:
            maxlevel (int): The maximum log level to allow.
            invert (bool, optional): If True, invert the filter logic (default is False).
        """
        self.maxlevel = maxlevel
        self.invert = invert

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Apply the filter to the given record.

        Args:
            record (logging.LogRecord): The logging record to filter.

        Returns:
            bool: True if the record passes the filter, False otherwise.
        """
        if self.invert:
            return record.levelno > self.maxlevel
        else:
            return record.levelno <= self.maxlevel
