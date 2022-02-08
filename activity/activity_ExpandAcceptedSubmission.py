import json
import os
from S3utility.s3_notification_info import parse_activity_data
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, download_helper
from activity.objects import Activity


class activity_ExpandAcceptedSubmission(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ExpandAcceptedSubmission, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ExpandAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Expands an accepted submission ZIP to a folder in an S3 bucket"
        )
        self.logger = logger

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # S3 expanded folder prefix
        self.s3_folder_prefix = "expanded_submissions"
        # S3 folder name to contain the expanded files and folders
        self.s3_files_folder = "expanded_files"

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # parse the input data
        input_filename, input_bucket_name, input_bucket_folder = parse_activity_data(
            data
        )
        self.logger.info(
            "%s, input_filename: %s, input_bucket_name: %s, input_bucket_folder: %s"
            % (self.name, input_filename, input_bucket_name, input_bucket_folder)
        )

        # store S3 zip file details in session
        run = data["run"]
        session = get_session(self.settings, data, run)
        session.store_value("run", run)
        session.store_value("input_filename", input_filename)
        session.store_value("input_bucket_name", input_bucket_name)
        session.store_value("input_bucket_folder", input_bucket_folder)

        # get article_id from the zip file name
        article_id = cleaner.article_id_from_zip_file(input_filename)
        session.store_value("article_id", article_id)

        # set the S3 bucket path to hold unzipped files
        expanded_folder = (
            self.s3_folder_prefix.lstrip("/").rstrip("/")
            + "/"
            + article_id
            + "/"
            + run
            + "/"
            + self.s3_files_folder
        )

        try:
            # Download zip from S3
            local_input_file = download_helper.download_file_from_s3(
                self.settings,
                input_filename,
                input_bucket_name,
                input_bucket_folder,
                self.directories.get("INPUT_DIR"),
            )
            # unzip using the elife-cleaner to get set of file name paths
            self.logger.info(
                "%s downloaded %s to %s" % (self.name, input_filename, local_input_file)
            )

            # extract zip contents
            self.logger.info("%s expanding file %s" % (self.name, input_filename))
            asset_file_name_map = cleaner.unzip_zip(
                local_input_file, self.directories.get("TEMP_DIR")
            )
            self.logger.info(
                "%s %s asset_file_name_map: %s"
                % (self.name, local_input_file, asset_file_name_map)
            )

            storage = storage_context(self.settings)

            for asset_file_name in asset_file_name_map.items():
                source_path = asset_file_name[1]
                dest_path = expanded_folder + "/" + asset_file_name[0]

                storage_resource_dest = (
                    self.settings.storage_provider
                    + "://"
                    + self.settings.bot_bucket
                    + "/"
                    + dest_path
                )
                self.logger.info(
                    "%s uploading %s to %s"
                    % (self.name, source_path, storage_resource_dest)
                )
                storage.set_resource_from_filename(storage_resource_dest, source_path)

            session.store_value("expanded_folder", expanded_folder)

        except Exception:
            self.logger.exception(
                "%s Exception when expanding accepted submission zip %s"
                % (self.name, input_filename)
            )

            return self.ACTIVITY_PERMANENT_FAILURE
        finally:
            self.clean_tmp_dir()

        return True
