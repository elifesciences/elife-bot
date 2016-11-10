import logging
from logging import handlers
import os
import random

def logger(logFile = None, setLevel = "INFO", identity = ""):
    """
    Create a logger, by specifying a unique (or same) logFile,
    set the level of logging, and optional identity for what is
    sending logging message, to identify multiple workers
    """
    logger = logging.getLogger('myapp')
    if(logFile):
        hdlr = handlers.WatchedFileHandler(os.getcwd() + os.sep + logFile)
    else:
        # No log file provided, use the stream handler
        hdlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s ' + identity + ' %(message)s', '%Y-%m-%dT%H:%M:%SZ')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(eval("logging." + setLevel))
    return logger

def identity(process_name):
    return "%s_%s" % (process_name, int(random.random() * 1000))
