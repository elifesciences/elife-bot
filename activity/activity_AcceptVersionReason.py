import activity
import json
import os
import re
from os import path
from jats_scraper import jats_scraper
import boto.s3
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import get_session
from provider.article_structure import ArticleInfo
import provider.article_structure as article_structure
import provider.s3lib as s3lib
from elifetools import xmlio

"""
ApplyVersionNumber.py activity
"""


class activity_ApplyVersionNumber(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ApplyVersionNumber"
        self.pretty_name = "Apply Version Number"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Rename expanded article files on S3 with a new version number"
        self.logger = logger

    def do_activity(self, data=None):

        try:

            self.expanded_bucket_name = (self.settings.publishing_buckets_prefix
                                         + self.settings.expanded_bucket)

            run = data['run']
            session = get_session(self.settings, data, run)
            version = session.get_value('version')
            article_id = session.get_value('article_id')
            # these are new values introduced with the input data to this workflow
            # calling set ensures they'll be there for all follow-on workflows
            session.store_value('version_reason', data.get('version_reason'))
            session.store_value('scheduled_publication_date', data.get('scheduled_publication_date'))

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start",
                                    "Starting applying version number to files for " + article_id)
        except Exception as e:
            self.logger.exception(str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        try:

            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

            if version is None:
                self.emit_monitor_event(self.settings, article_id, version, run,
                                        self.pretty_name, "error",
                                        "Error in applying version number to files for " + article_id +
                                        " message: No version available")
                return activity.activity.ACTIVITY_PERMANENT_FAILURE

            expanded_folder_name = session.get_value('expanded_folder')
            bucket_folder_name = expanded_folder_name.replace(os.sep, '/')
            self.rename_article_s3_objects(bucket_folder_name, version)

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end",
                                    "Finished applying version number to article " + article_id +
                                    " for version " + version + " run " + str(run))

        except Exception as e:
            self.logger.exception(str(e))
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error in applying version number to files for " + article_id +
                                    " message:" + str(e.message))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        return activity.activity.ACTIVITY_SUCCESS

    def rename_article_s3_objects(self, bucket_folder_name, version):
        """
        Main function to rename article objects on S3
        and apply the renamed file names to the article XML file
        """

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key,
                               host=self.settings.s3_hostname)
        bucket = s3_conn.lookup(self.expanded_bucket_name)

        # bucket object list
        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=bucket_folder_name + "/")

        # Get the old name to new name map
        file_name_map = self.build_file_name_map(s3_key_names, version)

        # log file names for reference
        if self.logger:
            self.logger.info('file_name_map: %s' %
                             json.dumps(file_name_map, sort_keys=True, indent=4))

        # rename_s3_objects(old_name_new_name_dict)
        self.rename_s3_objects(bucket, self.expanded_bucket_name, bucket_folder_name, file_name_map)

        # rewrite_and_upload_article_xml()
        xml_filename = self.find_xml_filename_in_map(file_name_map)
        self.download_file_from_bucket(bucket, bucket_folder_name, xml_filename)
        self.rewrite_xml_file(xml_filename, file_name_map)
        self.upload_file_to_bucket(bucket, bucket_folder_name, xml_filename)

    def download_file_from_bucket(self, bucket, bucket_folder_name, filename):

        key_name = bucket_folder_name + '/' + filename
        key = Key(bucket)
        key.key = key_name
        local_file = self.open_file_from_tmp_dir(filename, mode='wb')
        key.get_contents_to_file(local_file)
        local_file.close()

    def rewrite_xml_file(self, xml_filename, file_name_map):

        local_xml_filename = path.join(self.get_tmp_dir(), xml_filename)

        xmlio.register_xmlns()
        root, doctype_dict = xmlio.parse(local_xml_filename, return_doctype_dict=True)

        # Convert xlink href values
        total = xmlio.convert_xlink_href(root, file_name_map)

        # Start the file output
        reparsed_string = xmlio.output(root, type=None, doctype_dict=doctype_dict)
        f = open(local_xml_filename, 'wb')
        f.write(reparsed_string)
        f.close()

    def upload_file_to_bucket(self, bucket, bucket_folder_name, filename):

        local_filename = path.join(self.get_tmp_dir(), filename)
        key_name = bucket_folder_name + '/' + filename
        key = Key(bucket)
        key.key = key_name
        key.set_contents_from_filename(local_filename)


    def build_file_name_map(self, s3_key_names, version):

        file_name_map = {}

        for key_name in s3_key_names:
            filename = key_name.split("/")[-1]

            # Get the new file name
            file_name_map[filename] = None

            if article_structure.is_video_file(filename) is False:
                renamed_filename = self.new_filename(filename, version)
            else:
                # Keep video files named the same
                renamed_filename = filename

            if renamed_filename:
                file_name_map[filename] = renamed_filename
            else:
                if self.logger:
                    self.logger.info('there is no renamed file for ' + filename)

        return file_name_map

    def new_filename(self, old_filename, version):
        if re.search(ur'-v([0-9])[\.]', old_filename): #is version already in file name?
            new_filename = re.sub(ur'-v([0-9])[\.]', '-v' + str(version) + '.', old_filename)
        else:
            (file_prefix, file_extension) = article_structure.file_parts(old_filename)
            new_filename = file_prefix + '-v' + str(version) + '.' + file_extension
        return new_filename

    def rename_s3_objects(self, bucket, bucket_name, bucket_folder_name, file_name_map):
        # Rename S3 bucket objects directly
        for old_name, new_name in file_name_map.iteritems():
            # Do not need to rename if the old and new name are the same
            if old_name == new_name:
                continue

            if new_name is not None:
                old_s3_key = bucket_folder_name + '/' + old_name
                new_s3_key = bucket_folder_name + '/' + new_name

                # copy old key to new key
                key = bucket.copy_key(new_s3_key, bucket_name, old_s3_key)
                if isinstance(key, boto.s3.key.Key):
                    # delete old key
                    old_key = bucket.delete_key(old_s3_key)


    def find_xml_filename_in_map(self, file_name_map):
        for old_name, new_name in file_name_map.iteritems():
            info = ArticleInfo(new_name)
            if info.file_type == 'ArticleXML':
                return new_name

