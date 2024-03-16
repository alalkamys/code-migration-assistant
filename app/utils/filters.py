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
    A class to represent a maximum logging level filter.

    ...

    Attributes
    ----------
    maxlevel : int
        maximum log level

    Methods
    -------
    filter(record):
        compares incoming logging records level no and accept it if record.levelno < self.maxlevel.
    """

    def __init__(self, maxlevel: int):
        self.maxlevel = maxlevel

    def filter(self, record: LogRecord):
        """Filters incoming logging record.

        Returns:
            compares incoming logging records level no and accept it if record.levelno < self.maxlevel.
        """
        return record.levelno < self.maxlevel
