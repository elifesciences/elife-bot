from elifecleaner import configure_logging, parse

LOG_FILENAME = "elifecleaner.log"


def log_to_file(filename=None):
    "configure logging to file"
    return configure_logging(filename) if filename else configure_logging(LOG_FILENAME)


def check_ejp_zip(zip_file, tmp_dir):
    return parse.check_ejp_zip(zip_file, tmp_dir)
