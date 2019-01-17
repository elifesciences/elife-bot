import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import time
import importlib
from optparse import OptionParser

import provider.simpleDB as dblib
import provider.swfmeta as swfmetalib
import starter

"""
Cron job to check for workflows to start every five minutes, if applicable
"""

class cron_FiveMinute(object):

    def start(self, settings):

        ping_marker_id = "cron_FiveMinute"

        # Log
        logFile = "starter.log"
        logger = log.logger(logFile, settings.setLevel, ping_marker_id)

        # Data provider
        db = dblib.SimpleDB(settings)
        db.connect()

        # SWF meta data provider
        swfmeta = swfmetalib.SWFMeta(settings)
        swfmeta.connect()

        last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(
            workflow_id=ping_marker_id)

        # Start a ping workflow as a marker
        self.start_ping_marker(ping_marker_id, settings)

        # Check for S3 XML files that were updated since the last run
        date_format = "%Y-%m-%dT%H:%M:%S.000Z"

        # Date conversion
        time_tuple = time.gmtime(last_startTimestamp)
        last_startDate = time.strftime(date_format, time_tuple)

        logger.info('last run %s %s' % (ping_marker_id, last_startDate))

        # A conditional start for SendQueuedEmail
        #  Only start a workflow if there are emails in the queue ready to send
        item_list = db.elife_get_email_queue_items(
            query_type="count",
            date_scheduled_before=last_startDate)

        try:
            if int(item_list[0]["Count"]) > 0:
                # More than one email in the queue, start a workflow
                try:
                    starter_name = "starter_SendQueuedEmail"
                    self.import_starter_module(starter_name, logger)
                    s = self.get_starter_module(starter_name, logger)
                    s.start(settings=settings)
                except:
                    logger.info('Error: %s starting %s' % (ping_marker_id, starter_name))
                    logger.exception('')
        except:
            # Some error
            logger.info('Exception encountered starting %s: %s' % (ping_marker_id, last_startDate))

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

    def get_starter_module(self, starter_name, logger=None):
        """
        Given an starter_name, and if the starter module is already
        imported, load the module and return it
        """
        full_path = "starter." + starter_name + "." + starter_name + "()"
        f = None

        try:
            f = eval(full_path)
        except:
            if logger:
                logger.exception('')

        return f

    def import_starter_module(self, starter_name, logger=None):
        """
        Given an starter name as starter_name,
        attempt to lazy load the module when needed
        """
        try:
            module_name = "starter." + starter_name
            importlib.import_module(module_name)
            return True
        except ImportError:
            if logger:
                logger.exception('')
            return False

if __name__ == "__main__":

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = cron_FiveMinute()

    o.start(settings=settings)
