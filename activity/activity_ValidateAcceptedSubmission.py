import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from S3utility.s3_notification_info import parse_activity_data
from provider import cleaner, download_helper, utils
from activity.objects import Activity


class activity_ValidateAcceptedSubmission(Activity):
    "ValidateAcceptedSubmission activity"

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ValidateAcceptedSubmission, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "ValidateAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download zip file input from the bucket, parse it, check contents "
            + "and log warning or error messages."
        )

        # Track some values
        self.input_file = None
        self.activity_log_file = "cleaner.log"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"valid": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # configure log files for the cleaner provider
        # log to a common log file
        cleaner.log_to_file()
        # log file for this activity only
        cleaner.log_to_file(os.path.join(self.get_tmp_dir(), self.activity_log_file))

        # parse the input data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        self.logger.info(
            "%s, real_filename: %s, bucket_name: %s, bucket_folder: %s"
            % (self.name, real_filename, bucket_name, bucket_folder)
        )

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )

        self.logger.info("%s, downloaded file to %s" % (self.name, self.input_file))

        # unzip the file and validate
        try:
            self.statuses["valid"] = cleaner.check_ejp_zip(
                self.input_file, self.directories.get("TEMP_DIR")
            )
        except ParseError:
            self.logger.exception(
                "%s, XML ParseError exception in cleaner.check_ejp_zip for file %s"
                % (self.name, self.input_file)
            )
            return self.ACTIVITY_PERMANENT_FAILURE
        except Exception:
            self.logger.exception(
                "%s, unhandled exception in cleaner.check_ejp_zip for file %s"
                % (self.name, self.input_file)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.log_statuses(self.input_file)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )

    def clean_tmp_dir(self):
        "custom cleaning of temp directory in order to retain some files for debugging purposes"
        keep_dirs = []
        for dir_name, dir_path in self.directories.items():
            if dir_name in keep_dirs or not os.path.exists(dir_path):
                continue
            shutil.rmtree(dir_path)
