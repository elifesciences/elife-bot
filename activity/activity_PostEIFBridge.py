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
activity_PostEIFBridge.py activity
"""
import requests


class activity_PostEIFBridge(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PostEIFBridge"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Carries data from PreparePostEIF activity through to PostPerfectPublication"
        self.logger = logger

    def do_activity(self, data=None):
        try:

            article_path = data['article_path']
            article_id = data['article_id']
            version = data['version']
            run = data['run']
            self.set_monitor_property(self.settings, article_id, 'path',
                                  article_path, 'text', version=version)


            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF Bridge", "start",
                                "Starting " + article_id)

            published = data['published']

            # assemble data to start post-publication workflow
            expanded_folder = data['expanded_folder']
            status = data['status']

            update_date = data['update_date']

            run = data['run']
            eif_filename = data['eif_filename']
            follow_on_data = {
                'article_id': article_id,
                'version': version,
                'expanded_folder': expanded_folder,
                'update_date': update_date,
                'run': run,
                'status': status,
                'eif_location': eif_filename,
            }

            message = {
                'workflow_name': 'PostPerfectPublication',
                'workflow_data': follow_on_data
            }

            if published is True:

                # initiate post-publication workflow now

                sqs_conn = boto.sqs.connect_to_region(
                    self.settings.sqs_region,
                    aws_access_key_id=self.settings.aws_access_key_id,
                    aws_secret_access_key=self.settings.aws_secret_access_key)

                out_queue = sqs_conn.get_queue(self.settings.workflow_starter_queue)
                m = Message()
                m.set_body(json.dumps(message))
                out_queue.write(m)


                self.set_monitor_property(self.settings, article_id, 'publication-status',
                                          'published', "text", version=version)
            else:
                encoded_message = base64.encodestring(json.dumps(message))
                # store message in dashboard for later
                self.set_monitor_property(self.settings, article_id, "_publication-data",
                                          encoded_message, "text", version=version)
                self.set_monitor_property(self.settings, article_id, "publication-status",
                                          "ready to publish", "text", version=version)

        except Exception as e:
            self.logger.exception("Exception after submitting article EIF")
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF Bridge", "error",
                            "Error carrying over information after EIF For article " + article_id +
                            " message:" + str(e.message))
            return False


        self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF Bridge", "end",
                                "Finished Post EIF Bridge " + article_id)
        return True
