import activity
import json
from jats_scraper import jats_scraper
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from S3utility.s3_notification_info import S3NotificationInfo

"""
ConvertJATS.py activity
"""

class activity_ConvertJATS(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ConvertJATS"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Process a JATS xml file into .... something else"
        self.logger = logger
        # TODO : better exception handling

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        info = S3NotificationInfo.from_dict(data)

        if self.logger:
            self.logger.info("Converting file %s" % info.file_name)

        # TODO : create a utility class for the S3 work, may already be in the bot somewhere
        conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(info.bucket_name)
        key = Key(bucket)
        key.key = info.file_name
        xml = key.get_contents_as_string()
        if self.logger:
            self.logger.info("Downloaded contents of file %s" % info.file_name)

        json_output = jats_scraper.scrape(xml)

        if self.logger:
            self.logger.info("Scraped file %s" % info.file_name)

        # TODO (see note above about utility class for S3 work)
        output_name = info.file_name.replace('.xml', '.json')
        destination = conn.get_bucket(self.settings.jr_S3_NAF_bucket)
        destination_key = Key(destination)
        destination_key.key = output_name
        destination_key.set_contents_from_string(json_output)

        if self.logger:
            self.logger.info("Uploaded key %s to %s" % (output_name, self.settings.jr_S3_NAF_bucket))

        return True

