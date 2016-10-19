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

"""
activity_PreparePostEIF.py activity
"""
import requests


class activity_PreparePostEIF(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PreparePostEIF"
        self.pretty_name = "Prepare Post EIF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Prepare data for queueing for Post EIF"
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


        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting preparation of article for EIF " + article_id)

        try:
            eif_filename = session.get_value(run, 'eif_filename')
            eif_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket

            article_path = session.get_value(run, 'article_path')
            self.set_monitor_property(self.settings, article_id, 'path',
                                          article_path, 'text', version=version)

            expanded_folder = session.get_value(run, 'expanded_folder')
            status = session.get_value(run, 'status')

            update_date = session.get_value(run, 'update_date')

            carry_over_data = {
                'eif_filename': eif_filename,
                'eif_bucket':  eif_bucket,
                'passthrough': {
                    'article_id': article_id,
                    'version': version,
                    'run': run,
                    'article_path': article_path,
                    'expanded_folder': expanded_folder,
                    'status': status,
                    'update_date': update_date,
                }
            }

            message = carry_over_data

            sqs_conn = boto.sqs.connect_to_region(
                self.settings.sqs_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key)

            out_queue = sqs_conn.get_queue(self.settings.website_ingest_queue)
            m = Message()
            m.set_body(json.dumps(message))
            out_queue.write(m)

            #########


        except Exception as e:
            self.logger.exception("Exception when Preparing for PostEIF")
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "Error submitting EIF For article" + article_id +
                                    " message:" + str(e.message))
            return False

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                "Finished preparation of article for EIF " + article_id)
        return True
