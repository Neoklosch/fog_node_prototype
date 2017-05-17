import os
import errno
import sys
from logbook import Logger as LogbookLogger, FileHandler, StreamHandler
from fog_node_engine.configuration.configreader import config
from fog_node_engine.decorators.singleton import Singleton


@Singleton
class Logger(LogbookLogger):
    def __init__(self):
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
        log_handler = FileHandler('%s%s' % (self.logger_path, config['LOGGER']['file_name']))
        log_handler.push_application()
