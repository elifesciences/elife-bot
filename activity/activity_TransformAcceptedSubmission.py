import os
import json
import shutil
from S3utility.s3_notification_info import parse_activity_data
from provider import cleaner, download_helper
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_TransformAcceptedSubmission(Activity):
    "TransformAcceptedSubmission activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_TransformAcceptedSubmission, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "TransformAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download zip file input from the bucket, transform the files and the XML, "
            + "and upload the new zip file to an output bucket."
        )

        # Track some values
        self.input_file = None
        self.activity_log_file = "cleaner.log"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Track the success of some steps
        self.statuses = {"transform": None, "upload": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # configure log files for the cleaner provider
        cleaner_log_handers = []
        format_string = (
            "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
        )
        # log to a common log file
        cleaner_log_handers.append(cleaner.log_to_file(format_string=format_string))
        # log file for this activity only
        log_file_path = os.path.join(self.get_tmp_dir(), self.activity_log_file)
        cleaner_log_handers.append(
            cleaner.log_to_file(
                log_file_path,
                format_string=format_string,
            )
        )

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

        # transform the zip file
        self.logger.info(
            "%s, starting to transform zip file %s", self.name, self.input_file
        )
        try:
            new_zip_file_path = cleaner.transform_ejp_zip(
                self.input_file,
                self.directories.get("TEMP_DIR"),
                self.directories.get("OUTPUT_DIR"),
            )
            self.statuses["transform"] = True
        except Exception:
            log_message = (
                "%s, unhandled exception in cleaner.transform_ejp_zip for file %s"
                % (self.name, self.input_file)
            )
            self.logger.exception(log_message)
            self.log_statuses(self.input_file)
            return self.ACTIVITY_PERMANENT_FAILURE
        finally:
            # remove the log handlers
            for log_handler in cleaner_log_handers:
                cleaner.log_remove_handler(log_handler)

        # upload zip file to output bucket
        self.upload_zip(
            self.settings.accepted_submission_output_bucket, new_zip_file_path
        )
        self.statuses["upload"] = True

        self.log_statuses(self.input_file)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def upload_zip(self, output_bucket_name, file_name_path):
        "upload the zip to the bucket"
        # Get the file name from the full file path
        file_name = file_name_path.split(os.sep)[-1]

        # Create S3 object and save
        bucket_name = output_bucket_name
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        s3_folder_name = ""
        resource_dest = (
            storage_provider + bucket_name + "/" + s3_folder_name + file_name
        )
        storage.set_resource_from_filename(resource_dest, file_name_path)
        self.logger.info(
            "%s, copied %s to %s", self.name, file_name_path, resource_dest
        )

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
