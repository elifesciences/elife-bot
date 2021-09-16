import time
import provider.swfmeta as swfmetalib
from provider import utils
import starter.starter_helper as helper
from starter.objects import Starter

"""
Cron job to check for workflows to start every five minutes, if applicable
"""


class cron_FiveMinute(Starter):
    def __init__(self, settings=None, logger=None):
        super(cron_FiveMinute, self).__init__(settings, logger, "cron_FiveMinute")

    def start(self, settings):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow()

    def start_workflow(self):

        ping_marker_id = "cron_FiveMinute"

        # SWF meta data provider
        swfmeta = swfmetalib.SWFMeta(self.settings)
        swfmeta.connect()

        last_start_timestamp = (
            swfmeta.get_last_completed_workflow_execution_startTimestamp(
                workflow_id=ping_marker_id
            )
        )

        # Start a ping workflow as a marker
        helper.start_ping_marker(ping_marker_id, self.settings, self.logger)

        # Check for S3 XML files that were updated since the last run
        # Date conversion
        time_tuple = time.gmtime(last_start_timestamp)
        last_startdate = time.strftime(utils.DATE_TIME_FORMAT, time_tuple)

        self.logger.info("last run %s %s", ping_marker_id, last_startdate)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER = cron_FiveMinute()

    STARTER.start(settings=SETTINGS)
