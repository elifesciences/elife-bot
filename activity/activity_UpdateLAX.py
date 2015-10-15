import activity
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import requests

"""
UpdateLAX.py activity
"""


class activity_UpdateLAX(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "UpdateLAX"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Submit updated EIF file to LAX post-publication"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """

        article_id = data['article_id']
        version = data['version']
        run = data['run']
        eif_location = data['eif_location']

        self.emit_monitor_event(self.settings, article_id, version, run, "Update LAX", "start",
                                "Updating LAX ")
        try:

            eif_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket
            conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(eif_bucket)
            key = Key(bucket)
            key.key = eif_location
            eif_json_string = key.get_contents_as_string()
            lax_update_endpoint = self.settings.lax_update
            response = requests.post(lax_update_endpoint, data=eif_json_string)

            self.emit_monitor_event(self.settings, article_id, version, run, "Update LAX", "end",
                                    "Lax has been updated")

        except Exception as e:
            self.logger.exception("Exception when updating LAX")
            self.emit_monitor_event(self.settings, article_id, version, run, "Update LAX", "error",
                                    "Error updating LAX")
            return False

        return True
