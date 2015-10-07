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
        self.description = "Process a JATS xml file into EIF"
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

        self.emit_monitor_event(self.settings, article_id, version, run, "Convert JATS", "start",
                                "Starting conversion of article xml to EIF for " + article_id)

        try:

            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
            expanded_folder_name = session.get_value(self.get_workflowId(), 'expanded_folder')
            expanded_folder_bucket = self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
            print expanded_folder_name

            conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(expanded_folder_bucket)

            bucket_folder_name = expanded_folder_name.replace(os.sep, '/')
            (xml_key, xml_filename) = self.get_article_xml_key(bucket, bucket_folder_name)
            if xml_key is None:
                self.logger.error("Article XML path not found")
                return False

            if self.logger:
                self.logger.info("Converting file %s" % xml_filename)

            xml = xml_key.get_contents_as_string()
            if self.logger:
                self.logger.info("Downloaded contents of file %s" % xml_filename)

            json_output = jats_scraper.scrape(xml)

            if self.logger:
                self.logger.info("Scraped file %s" % xml_filename)

            output_folder = path.join(article_version_id, run)
            output_name = xml_filename.replace('.xml', '.json')
            output_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket
            output_path = path.join(output_folder, output_name)
            destination = conn.get_bucket(output_bucket)
            destination_key = Key(destination)
            destination_key.key = output_path.replace(os.sep, '/')
            destination_key.set_contents_from_string(json_output)

            if self.logger:
                self.logger.info("Uploaded key %s to %s" % (output_path, output_bucket))

            session.store_value(self.get_workflowId(), "eif_filename", output_path)
            eif_object = json.loads(json_output)
            session.store_value(self.get_workflowId(), 'article_path', eif_object.get('path'))
            self.emit_monitor_event(self.settings, article_id, version, run, "Post EIF", "error",
                                        "XML converted to EIF for article " + article_id + " to " + output_path)

        except Exception as e:
            self.logger.exception("Exception when converting article XML to EIF")
            self.emit_monitor_event(self.settings, article_id, version, run, "Convert JATS", "error",
                                    "Error in conversion of article xml to EIF for " + article_id +
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
