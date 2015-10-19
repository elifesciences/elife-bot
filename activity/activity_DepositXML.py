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
DepositXML.py activity
"""


class activity_DepositXML(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "DepositXML"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit XML file for markup service pre-publication"
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

        self.emit_monitor_event(self.settings, article_id, version, run, "Deposit XML", "start",
                                "Deposit article XML for markup service for article " + article_id)

        try:

            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
            expanded_folder_name = session.get_value(self.get_workflowId(), 'expanded_folder')
            expanded_folder_bucket = self.settings.publishing_buckets_prefix + self.settings.expanded_bucket

            conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(expanded_folder_bucket)

            bucket_folder_name = expanded_folder_name.replace(os.sep, '/')
            (xml_key, xml_filename) = self.get_article_xml_key(bucket, bucket_folder_name)
            if xml_key is None:
                self.logger.error("Article XML path not found")
                return False



            # output_folder = path.join(article_version_id, run)
            output_bucket = self.settings.publishing_buckets_prefix + self.settings.xml_bucket
            #output_path = path.join(output_folder, xml_filename)
            destination = conn.get_bucket(output_bucket)
            destination_key = Key(destination)
            #output_key = output_path.replace(os.sep, '/')
            destination_key.key = xml_filename
            destination_key.set_contents_from_string(xml_key.get_contents_as_string())

            if self.logger:
                self.logger.info("Uploaded key %s to %s" % (xml_filename, output_bucket))


            self.emit_monitor_event(self.settings, article_id, version, run, "Deposit XML", "success",
                                        "XML deposited for article " + article_id + " to " + xml_filename)

        except Exception as e:
            self.logger.exception("Exception when converting article XML to EIF")
            self.emit_monitor_event(self.settings, article_id, version, run, "Deposit XML", "error",
                                    "Error depositing XML for article " + article_id +
                                    " message:" + e.message)
            return False

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
