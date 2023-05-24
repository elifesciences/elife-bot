import os
import json
import shutil
from provider import article_processing, cleaner
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import AcceptedBaseActivity


class activity_OutputAcceptedSubmission(AcceptedBaseActivity):
    "OutputAcceptedSubmission activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_OutputAcceptedSubmission, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "OutputAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download files from a bucket folder, zip them, "
            "and copy to the output bucket."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Track the success of some steps
        self.statuses = {"download": None, "zip": None, "upload": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # download the all files from the bucket expanded folder
        try:
            download_all_files_from_bucket(
                storage,
                asset_file_name_map,
                self.directories.get("INPUT_DIR"),
                self.logger,
            )
            self.statuses["download"] = True
        except:
            log_message = (
                "%s, exception in download_all_files_from_bucket" " for file %s"
            ) % (
                self.name,
                input_filename,
            )
            self.logger.exception(log_message)
            self.statuses["download"] = False

        #  zip the files
        if self.statuses.get("download"):
            new_zip_file_path = cleaner.rezip(
                asset_file_name_map, self.directories.get("OUTPUT_DIR"), input_filename
            )
            self.statuses["zip"] = True

        if self.statuses.get("zip"):
            # upload zip file to output bucket
            self.upload_zip(
                self.settings.accepted_submission_output_bucket, new_zip_file_path
            )
            self.statuses["upload"] = True

        self.log_statuses(input_filename)

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


def download_all_files_from_bucket(storage, asset_file_name_map, to_dir, logger):
    "download files in asset_file_name_map from the S3 bucket expanded folder to the local disk"
    s3_files = [
        {"upload_file_nm": article_processing.file_name_from_name(key)}
        for key in asset_file_name_map
    ]
    cleaner.download_asset_files_from_bucket(
        storage, s3_files, asset_file_name_map, to_dir, logger
    )
