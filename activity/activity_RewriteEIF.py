import activity
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import requests
from provider import eif as eif_provider

"""
RewriteEIF.py activity
"""


class activity_RewriteEIF(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "RewriteEIF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Rewrite the EIF stored on S3 with new or updated values post-publication"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """

        article_id = data['article_id']
        version = data['version']
        run = data['run']
        eif_location = data['eif_location']
        update_date = data['update_date']

        self.emit_monitor_event(self.settings, article_id, version, run, "Rewrite EIF", "start",
                                "Rewriting EIF ")
        try:

            # Add update value to the EIF json
            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)
            eif_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket

            eif_json = eif_provider.read_eif_from_s3(conn, eif_bucket, eif_location)
            eif_json = eif_provider.add_update_date_to_json(eif_json, update_date, self.logger)
            eif_provider.write_eif_to_s3(conn, eif_json, eif_bucket, eif_location)

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Rewrite EIF", "end",
                                    "EIF has been updated, update_date " +
                                    str(update_date))

        except Exception as e:
            self.logger.exception("Exception when rewriting EIF")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Rewrite EIF", "error",
                                    "Error rewriting EIF")
            return False


        return True
