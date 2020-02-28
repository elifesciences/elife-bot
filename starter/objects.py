import random
import boto.swf

import log


LOG_FILE = "starter.log"


class Starter():

    # Base class
    def __init__(self, settings=None, logger=None):
        self.settings = settings
        self.logger = None
        self.conn = None

        # logging
        if logger:
            self.logger = logger
        else:
            self.instantiate_logger()

    def instantiate_logger(self):
        if not self.logger and self.settings:
            identity = "starter_%s" % int(random.random() * 1000)
            self.logger = log.logger(LOG_FILE, self.settings.setLevel, identity)

    def connect_to_swf(self):
        """connect to SWF"""
        # Simple connect
        self.conn = boto.swf.layer1.Layer1(
            self.settings.aws_access_key_id,
            self.settings.aws_secret_access_key)
