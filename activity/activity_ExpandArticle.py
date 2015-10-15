import json
from zipfile import ZipFile
import random
import uuid

import activity
import re
import os
from os.path import isfile, join
from os import listdir, makedirs
from os import path
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import Session
import requests

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

        # set up required connections
        conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        source_bucket = conn.get_bucket(info.bucket_name)
        dest_bucket = conn.get_bucket(self.settings.publishing_buckets_prefix + self.settings.expanded_bucket)
        session = Session(self.settings)

        article_id_match = re.match(ur'elife-(.*?)-', info.file_name)
        article_id = article_id_match.group(1)
        session.store_value(self.get_workflowId(), 'article_id', article_id)

        if self.logger:
            self.logger.info("Expanding file %s" % info.file_name)

        # extract any doi, version and updated date information from the filename
        version = None
        # zip name contains version information for previously archived zip files
        m = re.search(ur'-v([0-9]*?)[\.|-]', info.file_name)
        if m is not None:
            version = m.group(1)
        if version is None:
            version = self.get_next_version(article_id)
        if version == '-1':
            return False  # version could not be determined, exit workflow. Can't emit event as no version.

        sm = re.search(ur'.*?-.*?-(.*?)-', info.file_name)
        if sm is not None:
            status = sm.group(1)
        if status is None:
            return False  # version could not be determined, exit workflow. Can't emit event as no version.
        run = str(uuid.uuid4())
        # store version for other activities in this workflow execution
        session.store_value(self.get_workflowId(), 'version', version)

        # TODO : extract and store updated date if supplied

        article_version_id = article_id + '.' + version
        session.store_value(self.get_workflowId(), 'article_version_id', article_version_id)
        session.store_value(self.get_workflowId(), 'run', run)
        session.store_value(self.get_workflowId(), 'status', status)
        self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article", "start",
                                "Starting expansion of article " + article_id)
        self.set_monitor_property(self.settings, article_id, "article_id", article_id, "text")
        try:

            # download zip to temp folder
            tmp = self.get_tmp_dir()
            key = Key(source_bucket)
            key.key = info.file_name
            local_zip_file = self.open_file_from_tmp_dir(info.file_name, mode='wb')
            key.get_contents_to_file(local_zip_file)
            local_zip_file.close()

            folder_name = path.join(article_version_id, run)

            # extract zip contents
            content_folder = path.join(tmp, folder_name)
            makedirs(content_folder)
            with ZipFile(path.join(tmp, info.file_name)) as zf:
                zf.extractall(content_folder)

            # TODO : rename files (versions!)

            # TODO : edit xml and rename references

            upload_filenames = []
            for f in listdir(content_folder):
                if isfile(join(content_folder, f)) and f[0] != '.' and not f[0] == '_':
                    upload_filenames.append(f)

            for filename in upload_filenames:
                source_path = path.join(content_folder, filename)
                dest_path = path.join(folder_name, filename).replace(os.sep, '/')
                k = Key(dest_bucket)
                k.key = dest_path
                k.set_contents_from_filename(source_path)

            session.store_value(self.get_workflowId(), 'expanded_folder', folder_name)
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article", "end",
                                    "Finished expansion of article " + article_id +
                                    " for version " + version + " run " + str(run) + " into " + folder_name)
        except Exception as e:
            self.logger.exception("Exception when expanding article")
            self.emit_monitor_event(self.settings, article_id, version, run, "Expand Article", "error",
                                    "Error expanding article " + article_id + " message:" + e.message)
            return False

        return True

    def get_next_version(self, article_id):
        url = self.settings.lax_article_versions.replace('{article_id}', article_id)
        response = requests.get(url)
        if response.status_code is 200:
            high_version = 0
            data = response.json()
            for version in data:
                int_version = int(version)
                if int_version > high_version:
                    high_version = int_version
            return str(high_version + 1)
        elif response.status_code is 404:
            return "1"
        else:
            self.logger.error("Error obtaining version information from Lax" + response.status_code)
            return "-1"
        


