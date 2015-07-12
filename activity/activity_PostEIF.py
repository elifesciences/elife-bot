import activity
import json
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session

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
        eif_filename = session.get_value(self.get_workflowId(), 'eif_filename')
        eif_bucket = self.settings.jr_S3_EIF_bucket

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
        self.logger.info("POST response was %s" % r.status_code)
        return True

