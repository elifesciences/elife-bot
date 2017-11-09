import activity
import json
import datetime
from jats_scraper import jats_scraper
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import get_session
from provider.article_structure import get_article_xml_key

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

        run = data['run']
        session = get_session(self.settings, data, run)
        version = session.get_value('version')
        article_id = session.get_value('article_id')
        article_version_id = article_id + '.' + version


        self.emit_monitor_event(self.settings, article_id, version, run, "Convert JATS", "start",
                                "Starting conversion of article xml to EIF for " + article_id)

        try:

            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
            expanded_folder_name = session.get_value('expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix
                                      + self.settings.expanded_bucket)

            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)
            bucket = conn.get_bucket(expanded_folder_bucket)

            bucket_folder_name = expanded_folder_name
            (xml_key, xml_filename) = get_article_xml_key(bucket, bucket_folder_name)
            if xml_key is None:
                self.logger.error("Article XML path not found")
                return False

            if self.logger:
                self.logger.info("Converting file %s" % xml_filename)

            xml = xml_key.get_contents_as_string()
            if self.logger:
                self.logger.info("Downloaded contents of file %s" % xml_filename)

            json_output = jats_scraper.scrape(xml, article_version=version)

            # Add update date if it is in the session
            update_date = session.get_value('update_date')
            if update_date:
                json_output = self.add_update_date_to_json(json_output, update_date, xml_filename)

            if self.logger:
                self.logger.info("Scraped file %s" % xml_filename)

            output_folder = article_version_id + '/' + run
            output_name = xml_filename.replace('.xml', '.json')
            output_bucket = self.settings.publishing_buckets_prefix + self.settings.eif_bucket
            output_path = output_folder + '/' + output_name
            destination = conn.get_bucket(output_bucket)
            destination_key = Key(destination)
            output_key = output_path
            destination_key.key = output_key
            destination_key.set_contents_from_string(json_output)

            if self.logger:
                self.logger.info("Uploaded key %s to %s" % (output_path, output_bucket))

            session.store_value("eif_location", output_key)
            eif_object = json.loads(json_output)
            session.store_value('article_path', eif_object.get('path'))
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Convert JATS", "end",
                                    "XML converted to EIF for article " +
                                    article_id + " to " + output_key)

        except Exception as e:
            self.logger.exception("Exception when converting article XML to EIF")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Convert JATS", "error",
                                    "Error in conversion of article xml to EIF for " + article_id +
                                    " message:" + e.message)
            return False

        return True

    def add_update_date_to_json(self, json_string, update_date, xml_filename=None):
        """
        Update date is a string e.g. 2012-10-15T00:00:00Z format
        We want to add update: YYYY-MM-DD to the json
        xml_filename is just for logging purposes
        """
        try:
            json_obj = json.loads(json_string)
            updated_date = datetime.datetime.strptime(update_date, "%Y-%m-%dT%H:%M:%SZ")
            update_date_string = updated_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            json_obj['update'] = update_date_string
            json_string = json.dumps(json_obj)
        except:
            if self.logger:
                self.logger.error("Unable to set the update date in the json %s" %
                                  str(xml_filename))
        return json_string
