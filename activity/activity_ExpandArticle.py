import activity
import re
import json
from jats_scraper import jats_scraper
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import Session
from zipfile import ZipFile

"""
ExpandArticle.py activity
"""

class activity_ExpandArticle(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ExpandArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Expands an article ZIP to an expanded folder, renaming as required"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        info = S3NotificationInfo.from_dict(data)

        conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = conn.get_bucket(info.bucket_name)

        if self.logger:
            self.logger.info("Expanding file %s" % info.file_name)

        version = None
        # zip name contains version information
        match = re.match('-v(.*?)\.', info.file_name)
        if match is not None:
            version = match.group(1)
        if version is None:
            # TODO : get from API
            version = 1

        # download zip to temp folder
        tmp = self.get_tmp_dir()
        key = Key(bucket)
        key.key = info.file_name
        local_zip_file = self.open_file_from_tmp_dir(info.file_name, mode='w')
        key.get_contents_to_file(local_zip_file)
        local_zip_file.close()

        with ZipFile(tmp + '/' + info.file_name) as zf:
            zf.extractall(tmp)


        # unzip zip

        # rename folder

        # rename files

        # edit xml and rename references

        # TODO : set final expanded folder in session
        #session = Session(self.settings)
        #session.store_value(self.get_workflowId(), 'expanded_folder', 'expanded_' + info.file_name)

        return True

        # conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        # bucket = conn.get_bucket(info.bucket_name)
        # key = Key(bucket)
        # key.key = info.file_name
        # xml = key.get_contents_as_string()
        # if self.logger:
        #     self.logger.info("Downloaded contents of file %s" % info.file_name)
        #
        # json_output = jats_scraper.scrape(xml)
        #
        # if self.logger:
        #     self.logger.info("Scraped file %s" % info.file_name)
        #
        # # TODO (see note above about utility class for S3 work)
        # output_name = info.file_name.replace('.xml', '.json')
        # destination = conn.get_bucket(self.settings.jr_S3_NAF_bucket)
        # destination_key = Key(destination)
        # destination_key.key = output_name
        # destination_key.set_contents_from_string(json_output)
        #
        # if self.logger:
        #     self.logger.info("Uploaded key %s to %s" % (output_name, self.settings.jr_S3_NAF_bucket))

