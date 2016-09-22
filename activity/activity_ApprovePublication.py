import base64
import json
import activity
import os
import requests
import boto.sqs
from boto.sqs.message import Message
from provider import eif

"""
ConvertJATS.py activity
"""
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)


class activity_ApprovePublication(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ApprovePublication"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Approve a previously submitted article"
        self.rules = []
        self.info = None
        self.logger = logger
        # TODO : better exception handling

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        article_id = data['article_id']
        version = data['version']
        run = data['run']

        try:

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Approve Publication", "start",
                                    "Starting approval of article " + article_id)

            publication_data = data['publication_data']
            article_version_id = str(article_id) + '.' + str(version)

            destination = self.settings.drupal_approve_endpoint
            destination = destination + article_version_id + '.json'

            headers = {'content-type': 'application/json'}

            auth = None
            if self.settings.drupal_update_user and self.settings.drupal_update_user != '':
                auth = requests.auth.HTTPBasicAuth(self.settings.drupal_update_user,
                                                   self.settings.drupal_update_pass)
            r = requests.put(destination, data="{ \"publish\": \"1\" }", headers=headers, auth=auth)
            self.logger.info("PUT response was %s" % r.status_code)

            if r.status_code == 200:
                self.set_monitor_property(self.settings, article_id, 'publication-status',
                                          'published', "text", version=version)
                message = base64.decodestring(publication_data)

                message = self.modify_update_date(message, r)

                sqs_conn = boto.sqs.connect_to_region(
                    self.settings.sqs_region,
                    aws_access_key_id=self.settings.aws_access_key_id,
                    aws_secret_access_key=self.settings.aws_secret_access_key)

                out_queue = sqs_conn.get_queue(self.settings.workflow_starter_queue)
                m = Message()
                m.set_body(message)
                out_queue.write(m)

            else:
                self.emit_monitor_event(self.settings, article_id, version, run,
                                        "Approve Publication", "error",
                                        "Website ingest returned an error code: " +
                                        str(r.status_code))
                self.logger.error("Body:" + r.text)
                return False

        except Exception as e:
            self.logger.exception("Exception when submitting article EIF")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Approve Publication", "error",
                                    "Error approving article publication for " + article_id +
                                    " message:" + str(e.message))
            return False


        self.emit_monitor_event(self.settings, article_id, version, run,
                                "Approve Publication", "end",
                                "Finished approving article" + article_id +
                                " status was " + str(r.status_code))
        return True

    def modify_update_date(self, message, response):
        update_date = self.extract_update_date(
            self.workflow_data(message),
            response.json())

        if update_date:
            message_json = json.loads(message)
            if ("workflow_data" in message_json and
                "update_date" in message_json["workflow_data"]):
                message_json["workflow_data"]["update_date"] = update_date
                message = json.dumps(message_json)
        return message

    def workflow_data(self, message):
        message_json = json.loads(message)
        if "workflow_data" in message_json:
            return message_json["workflow_data"]
        return {}

    def extract_update_date(self, passthrough_json, response_json):
        return eif.extract_update_date(passthrough_json, response_json)
