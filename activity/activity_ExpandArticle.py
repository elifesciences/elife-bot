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

        storage_context = StorageContext(self.settings)

        session = Session(self.settings)

        filename_last_element = info.file_name[info.file_name.rfind('/')+1:]
        article_id_match = re.match(ur'elife-(.*?)-', filename_last_element)
        if article_id_match is None:
            self.logger.error("Name '%s' did not match expected pattern for article id" %
                              filename_last_element)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE
        article_id = article_id_match.group(1)
        session.store_value(self.get_workflowId(), 'article_id', article_id)

        if self.logger:
            self.logger.info("Expanding file %s" % info.file_name)

        # extract any doi, version and updated date information from the filename
        version = None
        status = None
        # zip name contains version information for previously archived zip files
        version = self.get_version_from_zip_filename(filename_last_element)
        if version is None:
            version = self.get_next_version(article_id)
        if version == '-1':
            self.logger.error("Name '%s' did not match expected pattern for version" %
                              filename_last_element)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE  # version could not be determined, will retry

        status = self.get_status_from_zip_filename(filename_last_element)
        if status is None:
            self.logger.error("Name '%s' did not match expected pattern for status" %
                              filename_last_element)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE  # status could not be determined, exit workflow.

        # Get the run value from the session, if available, otherwise set it
        run = session.get_value(self.get_workflowId(), 'run')
        if run is None:
            run = str(uuid.uuid4())

        # store version for other activities in this workflow execution
        session.store_value(self.get_workflowId(), 'version', version)

        # Extract and store updated date if supplied
        update_date = self.get_update_date_from_zip_filename(filename_last_element)
        if update_date:
            session.store_value(self.get_workflowId(), 'update_date', update_date)

        article_version_id = article_id + '.' + version
        session.store_value(self.get_workflowId(), 'article_version_id', article_version_id)
        session.store_value(self.get_workflowId(), 'run', run)
        session.store_value(self.get_workflowId(), 'status', status)
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

            session.store_value(self.get_workflowId(), 'expanded_folder', bucket_folder_name)
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
        url = self.settings.lax_article_versions.replace('{article_id}', article_id)
        response = requests.get(url, verify=self.settings.verify_ssl)
        if response.status_code == 200:
            high_version = 0
            data = response.json()
            for version in data:
                int_version = int(version)
                if int_version > high_version:
                    high_version = int_version
            return str(high_version + 1)
        elif response.status_code == 404:
            return "1"
        else:
            self.logger.error("Error obtaining version information from Lax" +
                              str(response.status_code))
            return "-1"

    def get_update_date_from_zip_filename(self, filename):
        m = re.search(ur'.*?-.*?-.*?-.*?-(.*?)\..*', filename)
        if m is None:
            return None
        else:
            try:
                raw_update_date = m.group(1)
                updated_date = datetime.datetime.strptime(raw_update_date, "%Y%m%d%H%M%S")
                return updated_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                return None

    def get_version_from_zip_filename(self, filename):
        m = re.search(ur'-v([0-9]+?)[\.|-]', filename)
        if m is None:
            return None
        else:
            return m.group(1)

    def get_status_from_zip_filename(self, filename):
        m = re.search(ur'.*?-.*?-(.*?)-', filename)
        if m is None:
            return None
        else:
            return m.group(1)
