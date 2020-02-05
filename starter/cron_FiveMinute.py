import boto.swf
import log
import time
import importlib
import provider.swfmeta as swfmetalib
from provider import utils

"""
Cron job to check for workflows to start every five minutes, if applicable
"""


class cron_FiveMinute(object):

    def start(self, settings):

        ping_marker_id = "cron_FiveMinute"

        # Log
        logFile = "starter.log"
        logger = log.logger(logFile, settings.setLevel, ping_marker_id)

        # SWF meta data provider
        swfmeta = swfmetalib.SWFMeta(settings)
        swfmeta.connect()

        last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(
            workflow_id=ping_marker_id)

        # Start a ping workflow as a marker
        self.start_ping_marker(ping_marker_id, settings)

        # Check for S3 XML files that were updated since the last run
        # Date conversion
        time_tuple = time.gmtime(last_startTimestamp)
        last_startDate = time.strftime(utils.DATE_TIME_FORMAT, time_tuple)

        logger.info('last run %s %s' % (ping_marker_id, last_startDate))

    def start_ping_marker(self, workflow_id, settings):
        """
        Start a ping workflow with a unique name to serve as a time marker
        for determining last time this was run
        """

        workflow_id = workflow_id
        workflow_name = "Ping"
        workflow_version = "1"
        child_policy = None
        execution_start_to_close_timeout = None
        input = None

        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name,
                                                     workflow_version, settings.default_task_list,
                                                     child_policy, execution_start_to_close_timeout,
                                                     input)

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                       'a running workflow with ID %s' % workflow_id)
            print(message)


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    o = cron_FiveMinute()

    o.start(settings=SETTINGS)
