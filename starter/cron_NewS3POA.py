import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import time

import provider.simpleDB as dblib
import provider.swfmeta as swfmetalib
from provider import utils
import starter.starter_helper as helper

"""
Cron job to check for new article S3 POA and start workflows
"""

class cron_NewS3POA(object):

    def start(self, settings):

        ping_marker_id = "cron_NewS3POA"

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
        # Quick hack - subtract 15 minutes,
        #   the time between S3Monitor running and this cron starter
        last_startTimestamp_minus_15 = last_startTimestamp - (60 * 15)
        time_tuple = time.gmtime(last_startTimestamp_minus_15)

        last_startDate = time.strftime(utils.DATE_TIME_FORMAT, time_tuple)

        logger.info('last run %s' % (last_startDate))

        xml_item_list = db.elife_get_POA_delivery_S3_file_items(
            last_updated_since=last_startDate)

        logger.info('POA files updated since %s: %s' % (last_startDate, str(len(xml_item_list))))

        if len(xml_item_list) <= 0:
            # No new XML
            pass
        else:
            # Found new XML files

            # Start a PackagePOA starter
            try:
                starter_name = "starter_PackagePOA"
                helper.import_starter_module(starter_name, logger)
                s = helper.get_starter_module(starter_name, logger)
                s.start(settings=settings, last_updated_since=last_startDate)
            except:
                logger.info('Error: %s starting %s' % (ping_marker_id, starter_name))
                logger.exception('')

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

    o = cron_NewS3POA()

    o.start(settings=SETTINGS)
