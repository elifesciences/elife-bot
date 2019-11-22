"functions shared by letterparser related activities"

import os
import docker
from letterparser import parse
import log

IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("letterparser_provider.log", 'INFO', IDENTITY, loggerName=__name__)


def parse_file(file_name, config):
    try:
        return parse.parse_file(file_name, config)
    except docker.errors.APIError:
        LOGGER.info('Error connecting to docker')
