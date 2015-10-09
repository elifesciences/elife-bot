import activity
import json
import os
from os import path
from jats_scraper import jats_scraper
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import Session
from provider.article_structure import ArticleInfo

"""
ApplyVersionNumber.py activity
"""


class activity_ApplyVersionNumber(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ApplyVersionNumber"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Rename expanded article files on S3 with a new version number"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """

        session = Session(self.settings)
        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        article_version_id = article_id + '.' + version
        run = session.get_value(self.get_workflowId(), 'run')

        self.emit_monitor_event(self.settings, article_id, version, run, "ApplyVersionNumber", "start",
                                "Starting applying version number to files for " + article_id)

        try:

            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
                
            # stub - todo


        except Exception as e:
            self.logger.exception("Exception when applying version number to article")
            self.emit_monitor_event(self.settings, article_id, version, run, "Convert JATS", "error",
                                    "Error in applying version number to files for " + article_id +
                                    " message:" + e.message)

        return True

    @staticmethod
    def get_article_xml_key(bucket, expanded_folder_name):
        files = bucket.list(expanded_folder_name + "/", "/")
        for bucket_file in files:
            key = bucket.get_key(bucket_file.key)
            filename = key.name.rsplit('/', 1)[1]
            info = ArticleInfo(filename)
            if info.file_type == 'ArticleXML':
                return key, filename
        return None
