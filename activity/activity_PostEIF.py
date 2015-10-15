import activity
import json
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session
import datetime
from S3utility.s3_sqs_message import S3SQSMessage
import boto.sqs
from boto.sqs.message import Message

"""
activity_PostEIF.py activity
"""
import requests


class activity_PostEIF(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PostEIF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Post a EIF JSON file to a REST service"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        session = Session(self.settings)
        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        run = session.get_value(self.get_workflowId(), 'run')

        self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "start",
                                "Starting submission of article EIF " + article_id)

        try:
            eif_filename = session.get_value(self.get_workflowId(), 'eif_filename')
            eif_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket

            if self.logger:
                self.logger.info("Posting file %s" % eif_filename)

            conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(eif_bucket)
            key = Key(bucket)
            key.key = eif_filename
            json_output = key.get_contents_as_string()
            destination = self.settings.drupal_EIF_endpoint

            headers = {'content-type': 'application/json'}
            r = requests.post(destination, data=json_output, headers=headers)
            self.logger.info("POST response was %s" % str(r.status_code))
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "start",
                                    "Finish submission of article " + article_id +
                                    " for version " + str(version) + " run " + str(run) + " the response status "
                                                                                          "was " + str(r.status_code))
            if r.status_code == 200:
                # TODO : article path will at some point be available in the respose
                article_path = session.get_value(self.get_workflowId(), 'article_path')
                self.set_monitor_property(self.settings, article_id, 'path', article_path, 'text')
                published = r.json().get('publish')
                if published == "1":
                    self.set_monitor_property(self.settings, article_id, 'publication_status', 'published', "text")
                else:
                    self.set_monitor_property(self.settings, article_id, 'publication_status', 'ready', "text")
            else:
                self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "error",
                                        "Website ingest returned an error code: " + str(r.status_code))
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "end",
                                    "Finished submitting EIF for article  " + article_id +
                                    " status was " + str(r.status_code))

            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "start",
                                    "Finish submission of article " + article_id +
                                    " for version " + str(version) + " run " + str(run) + " the response status ")
            try:
                # initiate post-publication workflow

                # assemble data
                expanded_folder = session.get_value(self.get_workflowId(), 'expanded_folder')
                status = session.get_value(self.get_workflowId(), 'status')

                update_date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                # TODO: need to replace line above with this once its in the session
                # update_date = session.get_value(self.get_workflowId(), 'update_date')

                sqs_conn = boto.sqs.connect_to_region(self.settings.sqs_region,
                                                      aws_access_key_id=self.settings.aws_access_key_id,
                                                      aws_secret_access_key=self.settings.aws_secret_access_key)
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
                out_queue = sqs_conn.get_queue(self.settings.workflow_starter_queue)
                m = Message()
                m.set_body(json.dumps(message))
                out_queue.write(m)


            except Exception as e:
                self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "error",
                                        "Website ingest returned an error code: " + str(r.status_code))
                return False
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "end",
                                    "Finished submitting EIF for article  " + article_id +
                                    " status was " + str(r.status_code))

        except Exception as e:
            self.logger.exception("Exception when submitting article EIF")
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "error",
                                    "Error submitting EIF For article" + article_id + " message:" + e.message)
            return False
        return True
