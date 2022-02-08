import logging
import re
from elifecleaner import LOGGER, configure_logging, parse, transform, zip_lib

LOG_FILENAME = "elifecleaner.log"


def article_id_from_zip_file(zip_file):
    "try to get an article id numeric string from a zip file name"
    id_match_pattern = re.compile(r".*\-(\d+).*\.zip$")
    matches = id_match_pattern.match(zip_file)
    if matches:
        return matches.group(1)
    return zip_file


def log_to_file(filename=None, level=logging.INFO, format_string=None):
    "configure logging to file"
    if not filename:
        filename = LOG_FILENAME
    return configure_logging(filename, level, format_string)


def log_remove_handler(handler):
    LOGGER.removeHandler(handler)


def unzip_zip(zip_file, tmp_dir):
    return zip_lib.unzip_zip(zip_file, tmp_dir)


def check_ejp_zip(zip_file, tmp_dir):
    return parse.check_ejp_zip(zip_file, tmp_dir)


def transform_ejp_zip(zip_file, tmp_dir, output_dir):
    return transform.transform_ejp_zip(zip_file, tmp_dir, output_dir)
