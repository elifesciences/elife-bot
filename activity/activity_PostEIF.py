import activity
import json
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from S3utility.s3_notification_info import S3NotificationInfo

"""
activity_PostNAF.py activity
"""
import requests

class activity_PostNAF(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PostNAF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Post a NAF JSON file to a REST service"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        # TODO : better exception handling
        info = S3NotificationInfo.from_dict(data)

        naf_filename = info.file_name.replace('.xml', '.json')
        naf_bucket = self.settings.jr_S3_NAF_bucket

        if self.logger:
            self.logger.info("Posting file %s" % naf_filename)

        conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(naf_bucket)
        key = Key(bucket)
        key.key = naf_filename
        json_output = key.get_contents_as_string()
        destination = self.settings.drupal_naf_endpoint

        # TODO : address file naming
        headers = {'content-type': 'application/json'}
        r = requests.post(destination, data=json_output, headers=headers)
        self.logger.info("POST response was %s" % r.status_code)
        return True

