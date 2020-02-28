import random
import log


LOG_FILE = "starter.log"


class Starter():

    # Base class
    def __init__(self, settings, logger=None):
        self.settings = settings

        # logging
        if logger:
            self.logger = logger
        else:
            identity = "starter_%s" % int(random.random() * 1000)
            self.logger = log.logger(LOG_FILE, settings.setLevel, identity)
