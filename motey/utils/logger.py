import errno
import os
import sys

from logbook import Logger as LogbookLogger, FileHandler, StreamHandler

from motey.configuration.configreader import config


class Logger(LogbookLogger):
    """
    Wrapper to configure the LogbookLogger.
    """

    def __init__(self):
        """
        Constructor of the Logger.
        Configures them and create the path to the output file if necessary.
        """
        super().__init__(config['LOGGER']['name'])
        self.logger_path = config['LOGGER']['log_path']
        try:
            os.makedirs(self.logger_path)
        except OSError as oserror:
            if oserror.errno == errno.EEXIST and os.path.isdir(self.logger_path):
                pass
            else:
                raise

        StreamHandler(sys.stdout).push_application()
        FileHandler('%s%s' % (self.logger_path, config['LOGGER']['file_name'])).push_application()
