import base64
from requests.auth import HTTPBasicAuth
import activity
import json
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session
import datetime
import boto.sqs
from boto.sqs.message import Message
import provider.lax_provider as lax_provider

"""
activity_IngestToLax.py activity
"""
import requests


class activity_IngestToLax(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "IngestToLax"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Prepare data and queue for Lax consumption"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')
        status = session.get_value(run, 'status')

        eif_location = "" #not available yet

        self.emit_monitor_event(self.settings, article_id, version, run, "Ingest To Lax", "start",
                                "Starting preparation of article for Lax " + article_id)

        try:
            expanded_folder = session.get_value(run, 'expanded_folder')
            message = lax_provider.prepare_action_message(self.settings,
                                                          article_id, run, expanded_folder, version, status, eif_location, 'ingest')
            sqs_conn = boto.sqs.connect_to_region(
                            self.settings.sqs_region,
                            aws_access_key_id=self.settings.aws_access_key_id,
                            aws_secret_access_key=self.settings.aws_secret_access_key)
            out_queue = sqs_conn.get_queue(self.settings.xml_info_queue)
            m = Message()
            m.set_body(json.dumps(message))
            out_queue.write(m)

            #########

        except Exception as e:
            self.logger.exception("Exception when Preparing Ingest for Lax")
            self.emit_monitor_event(self.settings, article_id, version, run, "Ingest To Lax", "error",
                                    "Error preparing or sending message to lax" + article_id +
                                    " message:" + str(e.message))
            return False

        self.emit_monitor_event(self.settings, article_id, version, run, "Ingest To Lax", "end",
                                "Finished preparation of article for Lax. Ingest sent to Lax" + article_id)
        return True
