import json
from zipfile import ZipFile
import uuid

import activity
import re
import os
from os.path import isfile, join
from os import listdir, makedirs
from os import path
import datetime
from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import Session
import requests
from provider.storage_provider import StorageContext
from provider.article_structure import ArticleInfo
import provider.lax_provider as lax_provider

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

        run = data['run']

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        info = S3NotificationInfo.from_dict(data)

        storage_context = StorageContext(self.settings)

        session = Session(self.settings)

        # filename_last_element = info.file_name[info.file_name.rfind('/')+1:]
        # article_id_match = re.match(ur'elife-(.*?)-', filename_last_element)
        # if article_id_match is None:
        #     self.logger.error("Name '%s' did not match expected pattern for article id" %
        #                       filename_last_element)
        #     return activity.activity.ACTIVITY_PERMANENT_FAILURE

        filename_last_element = session.get_value(run, 'filename_last_element')
        # zip name contains version information for previously archived zip files
        article_structure = ArticleInfo(filename_last_element)
        article_id = article_structure.article_id
        session.store_value(run, 'article_id', article_id)
        session.store_value(run, 'file_name', info.file_name)

        if self.logger:
            self.logger.info("Expanding file %s" % info.file_name)

        version = session.get_value(run, 'version')
        # version = article_structure.get_version_from_zip_filename()
        # if version is None:
        #     version = self.get_next_version(article_id)
        # if version == '-1':
        #     self.logger.error("Name '%s' did not match expected pattern for version" %
        #                       filename_last_element)
        #     return activity.activity.ACTIVITY_PERMANENT_FAILURE  # version could not be determined, will retry

        # store version for other activities in this workflow execution
        #session.store_value(run, 'version', version)


        status = article_structure.status
        if status is None or (status != 'vor' and status != 'poa'):
            self.logger.error("Name '%s' did not match expected pattern for status" %
                              filename_last_element)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE  # status could not be determined, exit workflow.



        # Extract and store updated date if supplied
        update_date = article_structure.get_update_date_from_zip_filename()
        if update_date:
            session.store_value(run, 'update_date', update_date)

        article_version_id = article_id + '.' + version
        session.store_value(run, 'article_version_id', article_version_id)
        session.store_value(run, 'run', run)
        session.store_value(run, 'status', status)
        self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article", "start",
                                "Starting expansion of article " + article_id)
        self.set_monitor_property(self.settings, article_id, "article-id", article_id, "text")
        self.set_monitor_property(self.settings, article_id, "publication-status",
                                  "publication in progress", "text",
                                  version=version)

        try:
            # download zip to temp folder
            tmp = self.get_tmp_dir()
            local_zip_file = self.open_file_from_tmp_dir(filename_last_element, mode='wb')
            storage_resource_origin = self.settings.storage_provider + "://" + info.bucket_name + "/" + info.file_name
            storage_context.get_resource_to_file(storage_resource_origin, local_zip_file)
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

            bucket_folder_name = article_version_id + '/' + run
            for filename in upload_filenames:
                source_path = path.join(content_folder, filename)
                dest_path = bucket_folder_name + '/' + filename
                storage_resource_dest = self.settings.storage_provider + "://" + self.settings.publishing_buckets_prefix + \
                                        self.settings.expanded_bucket + "/" + dest_path
                storage_context.set_resource_from_file(storage_resource_dest, source_path)

            self.clean_tmp_dir()

            session.store_value(run, 'expanded_folder', bucket_folder_name)
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article",
                                    "end", "Finished expansion of article " + article_id +
                                    " for version " + version + " run " + str(run) +
                                    " into " + bucket_folder_name)
        except Exception as e:
            self.logger.exception("Exception when expanding article")
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article",
                                    "error", "Error expanding article " + article_id +
                                    " message:" + e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        return True

    def get_next_version(self, article_id):
        version = lax_provider.article_highest_version(article_id, self.settings)
        if isinstance(version, (int,long)) and version >= 1:
            version = str(version + 1)
        if version is None:
            return "-1"
        return version