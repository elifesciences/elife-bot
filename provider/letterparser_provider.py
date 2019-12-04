"functions shared by letterparser related activities"

import os
import docker
from letterparser import parse
from letterparser.conf import raw_config, parse_raw_config
import log

IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("letterparser_provider.log", 'INFO', IDENTITY, loggerName=__name__)


def letterparser_config(settings):
    """parse the config values from letterparser.cfg"""
    return parse_raw_config(raw_config(
        settings.letterparser_config_section,
        settings.letterparser_config_file))


def parse_file(file_name, config):
    try:
        return parse.parse_file(file_name, config)
    except docker.errors.APIError:
        LOGGER.info('Error connecting to docker')
        raise
