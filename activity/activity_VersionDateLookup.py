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
from provider.execution_context import get_session
import requests
from provider.storage_provider import storage_context
from provider.article_structure import ArticleInfo
import provider.lax_provider as lax_provider


class activity_VersionDateLookup(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VersionDateLookup"
        self.pretty_name = "Version Date Lookup"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Looks up version date on Lax endpoints and stores version date in session " \
                           "(Currently used in Silent corrections only)"
        self.logger = logger

    def do_activity(self, data=None):

        try:
            run = data['run']
            session = get_session(self.settings, data, run)
            version = session.get_value('version')
            filename = session.get_value('filename_last_element')

            article_structure = ArticleInfo(filename)

            version_date, error = self.get_version(self.settings, article_structure, article_structure.article_id, version)


            if error is not None:
                self.logger.error(error)
                self.emit_monitor_event(self.settings, article_structure.article_id, version, data['run'],
                                        self.pretty_name, "error",
                                        " ".join(("Error Looking up version article", article_structure.article_id,
                                                 "message:", error)))
                return activity.activity.ACTIVITY_PERMANENT_FAILURE

            self.emit_monitor_event(self.settings, article_structure.article_id, version, data['run'],
                                    self.pretty_name, "end",
                                    " ".join(("Finished Version Lookup for article", article_structure.article_id,
                                    "version:", version)))

            session.store_value('update_date', version_date)

            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception("Exception when trying to Lookup next version")
            self.emit_monitor_event(self.settings, article_structure.article_id, version, data['run'], self.pretty_name,
                                    "error", " ".join(("Error looking up version for article",
                                                      article_structure.article_id, "message:", str(e))))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def get_version(self, settings, article_structure, article_id, version):
        try:
            version_date = article_structure.get_update_date_from_zip_filename()
            if version_date:
                return version_date, None
            version_date = lax_provider.article_version_date_by_version(article_id, version, settings)
            return version_date, None
        except Exception as e:
            error_message = "Exception when looking up version Date. Message: " + str(e)
            return version_date, error_message

    def execute_function(self, the_function, arg1, arg2):
        return the_function(arg1, arg2)
