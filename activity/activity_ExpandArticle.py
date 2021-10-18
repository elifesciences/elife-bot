import json
from zipfile import ZipFile
import uuid
import re
import os
from os.path import isfile, join
from os import listdir, makedirs
from os import path
import datetime
from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import get_session
import requests
from provider.storage_provider import storage_context
from provider.article_structure import ArticleInfo
from provider import lax_provider, utils
from activity.objects import Activity

"""
ExpandArticle.py activity
"""

class activity_ExpandArticle(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ExpandArticle, self).__init__(
            settings, logger, conn, token, activity_task)

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

        run = data['run']
        session = get_session(self.settings, data, run)
        article_id = session.get_value('article_id')

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        info = S3NotificationInfo.from_dict(data)

        storage = storage_context(self.settings)

        session = get_session(self.settings, data, run)

        filename_last_element = session.get_value('filename_last_element')

        article_structure = ArticleInfo(filename_last_element)
        session.store_value('file_name', info.file_name)

        if self.logger:
            self.logger.info("Expanding file %s" % info.file_name)

        version = session.get_value('version')

        status = article_structure.status
        if status is None or (status != 'vor' and status != 'poa'):
            self.logger.error("Name '%s' did not match expected pattern for status" %
                              filename_last_element)
            return self.ACTIVITY_PERMANENT_FAILURE  # status could not be determined, exit workflow.

        article_version_id = utils.pad_msid(article_id) + '.' + version
        session.store_value('article_version_id', article_version_id)
        session.store_value('run', run)
        session.store_value('status', status)
        self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article", "start",
                                "Starting expansion of article " + article_id)


        try:
            # download zip to temp folder
            tmp = self.get_tmp_dir()
            local_zip_file = self.open_file_from_tmp_dir(filename_last_element, mode='wb')
            storage_resource_origin = self.settings.storage_provider + "://" + info.bucket_name + "/" + info.file_name
            storage.get_resource_to_file(storage_resource_origin, local_zip_file)
            local_zip_file.close()

            # extract zip contents
            folder_name = path.join(article_version_id, run)
            content_folder = path.join(tmp, folder_name)
            makedirs(content_folder)
            with ZipFile(path.join(tmp, filename_last_element)) as zf:
                zf.extractall(content_folder)

            upload_filenames = []
            for f in listdir(content_folder):
                if isfile(join(content_folder, f)) and f[0] != '.' and not f[0] == '_':
                    upload_filenames.append(f)
            self.check_filenames(upload_filenames)

            bucket_folder_name = article_version_id + '/' + run
            for filename in upload_filenames:
                source_path = path.join(content_folder, filename)
                dest_path = bucket_folder_name + '/' + filename
                storage_resource_dest = self.settings.storage_provider + "://" + self.settings.publishing_buckets_prefix + \
                                        self.settings.expanded_bucket + "/" + dest_path
                storage.set_resource_from_filename(storage_resource_dest, source_path)

            self.clean_tmp_dir()

            session.store_value('expanded_folder', bucket_folder_name)
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article",
                                    "end", "Finished expansion of article " + article_id +
                                    " for version " + version + " run " + str(run) +
                                    " into " + bucket_folder_name)
        except Exception as exception:
            self.logger.exception("Exception when expanding article")
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article",
                                    "error", "Error expanding article " + article_id +
                                    " message:" + str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        return True

    def get_next_version(self, article_id):
        version = lax_provider.article_highest_version(article_id, self.settings)
        if isinstance(version, int) and version >= 1:
            version = str(version + 1)
        if version is None:
            return "-1"
        return version

    def check_filenames(self, filenames):
        xml_found = False
        for filename in filenames:
            if filename.endswith(".xml"):
                xml_found = True
        if not xml_found:
            raise RuntimeError("No .xml file found. List of files found is %s" % filenames)
