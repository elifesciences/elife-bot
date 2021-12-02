import shutil
import datetime
import os
import re

import boto.swf
import dashboard_queue
from provider import utils

"""
Amazon SWF activity base class
"""


class Activity(object):

    ACTIVITY_SUCCESS = "ActivitySuccess"
    ACTIVITY_TEMPORARY_FAILURE = "ActivityTemporaryFailure"
    ACTIVITY_PERMANENT_FAILURE = "ActivityPermanentFailure"
    ACTIVITY_EXIT_WORKFLOW = "ActivityExitWorkflow"

    # Base class
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        self.settings = settings
        self.logger = logger
        self.result = None
        self.conn = conn
        self.token = token
        self.activity_task = activity_task

        # SWF Defaults, most are set in derived classes or at runtime
        try:
            self.domain = self.settings.domain
        except KeyError:
            self.domain = None

        try:
            self.task_list = self.settings.default_task_list
        except KeyError:
            self.task_list = None

        self.name = None
        self.pretty_name = None
        self.version = None
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 10
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = None

        self.tmp_base_dir = "tmp"
        self.tmp_dir = None
        self.directories = None

    def describe(self):
        """
        Describe activity type from SWF, to confirm it exists
        Requires object to have an active connection to SWF using boto
        """
        if (
            self.conn is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        try:
            response = self.conn.describe_activity_type(
                self.domain, self.name, self.version
            )
        except boto.exception.SWFResponseError:
            response = None

        return response

    def register(self):
        """
        Register the activity type with SWF, if it does not already exist
        Requires object to have an active connection to SWF using boto
        """
        if (
            self.conn is None
            or self.domain is None
            or self.name is None
            or self.version is None
        ):
            return None

        if self.describe() is None:
            response = self.conn.register_activity_type(
                str(self.domain),
                str(self.name),
                str(self.version),
                str(self.task_list),
                str(self.default_task_heartbeat_timeout),
                str(self.default_task_schedule_to_close_timeout),
                str(self.default_task_schedule_to_start_timeout),
                str(self.default_task_start_to_close_timeout),
                str(self.description),
            )

            return response

    def get_workflowId(self):
        """
        Get the workflowId from the SWF activity_task
        if it is available
        """
        workflowId = None
        if self.activity_task is None:
            return None

        try:
            workflowId = self.activity_task["workflowExecution"]["workflowId"]
        except KeyError:
            workflowId = None

        return workflowId

    def get_activityId(self):
        """
        Get the activityId from the SWF activity_task
        if it is available
        """
        activityId = None
        if self.activity_task is None:
            return None

        try:
            activityId = self.activity_task["activityId"]
        except KeyError:
            activityId = None

        return activityId

    def make_tmp_dir(self):
        """
        Check or create temporary directory for this activity
        """
        # Try and make the based tmp directory, if it does not exist
        if self.tmp_base_dir:
            try:
                os.mkdir(self.tmp_base_dir)
            except OSError:
                pass

        # Create a new directory specifically for this activity
        dir_name = datetime.datetime.utcnow().strftime("%Y-%m-%d.%H.%M.%S")
        workflowId = self.get_workflowId()
        activityId = self.get_activityId()
        try:
            domain = self.settings.domain
        except:
            domain = None
        if domain:
            # Use regular expression to strip out messy symbols
            domain_safe = re.sub(r"\W", "", domain)
            dir_name += "." + domain_safe
        if workflowId:
            # Use regular expression to strip out messy symbols
            workflowId_safe = re.sub(r"\W", "", workflowId)
            dir_name += "." + workflowId_safe
        if activityId:
            # Use regular expression to strip out messy symbols
            activityId_safe = re.sub(r"\W", "", activityId)
            dir_name += "." + activityId_safe

        if self.tmp_base_dir:
            full_dir_name = self.tmp_base_dir + os.sep + dir_name
        else:
            full_dir_name = dir_name

        try:
            os.mkdir(full_dir_name)
            self.tmp_dir = full_dir_name
        except OSError:
            # Directory may already exist, happens when running tests, check if it exists
            if os.path.isdir(full_dir_name):
                self.tmp_dir = full_dir_name

        if not self.tmp_dir:
            raise RuntimeError("Cannot create temporary directory %s" % full_dir_name)

    def get_tmp_dir(self):
        """
        Get the temporary file directory, but if not set
        then make the directory
        """
        if self.tmp_dir:
            return self.tmp_dir
        else:
            self.make_tmp_dir()

        return self.tmp_dir

    def make_activity_directories(self, dir_names=None):
        """
        Create the directories in the activity tmp_dir
        """
        if not dir_names and self.directories and hasattr(self.directories, "values"):
            dir_names = list(self.directories.values())
        if not dir_names:
            self.logger.info("No dir_names to create in make_activity_directories()")
            return None
        # Now try to find or make directories
        for dir_name in dir_names:
            if os.path.isdir(dir_name):
                # directory exists, continue
                continue
            try:
                os.mkdir(dir_name)
            except OSError as exception:
                self.logger.exception(str(exception))
                raise
        return True

    def open_file_from_tmp_dir(self, filename, mode="r"):
        """
        Read the file from the tmp_dir
        """
        tmp_dir = self.get_tmp_dir()

        if tmp_dir:
            full_filename = tmp_dir + os.sep + filename
        else:
            full_filename = filename

        f = open(full_filename, mode)
        return f

    def clean_tmp_dir(self):

        tmp_dir = self.get_tmp_dir()
        shutil.rmtree(tmp_dir)
        self.tmp_dir = None

    def emit_activity_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                status,
                message,
            )
            return True
        except Exception as exception:
            self.logger.exception(
                "Exception emitting %s message. Details: %s"
                % (str(status), str(exception))
            )

    def message_activity_name(self):
        "the name for the activity to use in emit messages"
        if self.pretty_name:
            return str(self.pretty_name)
        return str(self.name)

    def emit_activity_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_activity_message(
            article_id,
            version,
            run,
            "start",
            "Starting " + self.message_activity_name() + " for " + str(article_id),
        )

    def emit_activity_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_activity_message(
            article_id,
            version,
            run,
            "end",
            "Finished " + self.message_activity_name() + " for " + str(article_id),
        )

    @staticmethod
    def emit_monitor_event(
        settings, item_identifier, version, run, event_type, status, message
    ):
        message = dashboard_queue.build_event_message(
            utils.pad_msid(item_identifier),
            version,
            run,
            event_type,
            datetime.datetime.now(),
            status,
            message,
        )

        dashboard_queue.send_message(message, settings)

    @staticmethod
    def set_monitor_property(
        settings, item_identifier, name, value, property_type, version=0
    ):
        message = dashboard_queue.build_property_message(
            utils.pad_msid(item_identifier), version, name, value, property_type
        )
        dashboard_queue.send_message(message, settings)
