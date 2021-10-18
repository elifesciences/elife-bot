import logging
from elifecleaner import LOGGER, configure_logging, parse

LOG_FILENAME = "elifecleaner.log"


def log_to_file(filename=None, level=logging.INFO, format_string=None):
    "configure logging to file"
    if not filename:
        filename = LOG_FILENAME
    return configure_logging(filename, level, format_string)


def log_remove_handler(handler):
    LOGGER.removeHandler(handler)


def check_ejp_zip(zip_file, tmp_dir):
    return parse.check_ejp_zip(zip_file, tmp_dir)
