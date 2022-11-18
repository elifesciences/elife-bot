import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from provider import article_processing, cleaner
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


REPAIR_XML = False


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
            "Download accepted submission files from a bucket folder, "
            + "transform the files and the XML, "
            + "and upload the modified files to the bucket folder."
        )

        # Track some values
        self.activity_log_file = "cleaner.log"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Track the success of some steps
        self.statuses = {"download": None, "transform": None, "upload": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        run = data["run"]
        session = get_session(self.settings, data, run)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        log_file_path = os.path.join(
            self.get_tmp_dir(), self.activity_log_file
        )  # log file for this activity only
        cleaner_log_handers = cleaner.configure_activity_log_handlers(log_file_path)

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # get list of bucket objects from expanded folder
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        self.logger.info(
            "%s, asset_file_name_map: %s" % (self.name, asset_file_name_map)
        )

        # find S3 object for article XML and download it
        xml_file_path = cleaner.download_xml_file_from_bucket(
            self.settings,
            asset_file_name_map,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # download the code files so they can be modified
        try:
            download_code_files_from_bucket(
                storage,
                xml_file_path,
                asset_file_name_map,
                self.directories.get("INPUT_DIR"),
                self.logger,
            )
            self.statuses["download"] = True
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in download_code_files_from_bucket"
                " parsing XML file %s for file %s"
            ) % (
                self.name,
                article_processing.file_name_from_name(xml_file_path),
                input_filename,
            )
            self.logger.exception(log_message)
            cleaner.LOGGER.exception(log_message)
            self.statuses["download"] = False
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        # PRC XML changes
        if session.get_value("prc_status"):
            cleaner.transform_prc(xml_file_path, input_filename)

        # transform the zip file
        if self.statuses.get("download"):
            self.logger.info(
                "%s, starting to transform zip file %s", self.name, input_filename
            )
            try:
                new_asset_file_name_map = cleaner.transform_ejp_files(
                    asset_file_name_map,
                    self.directories.get("TEMP_DIR"),
                    input_filename,
                )
                self.statuses["transform"] = True
            except Exception:
                log_message = (
                    "%s, unhandled exception in cleaner.transform_ejp_files for file %s"
                    % (self.name, input_filename)
                )
                self.logger.exception(log_message)
                self.statuses["transform"] = False
                new_asset_file_name_map = {}
            finally:
                # remove the log handlers
                for log_handler in cleaner_log_handers:
                    cleaner.log_remove_handler(log_handler)

            self.logger.info(
                "%s, new_asset_file_name_map: %s" % (self.name, new_asset_file_name_map)
            )

        # files to upload and delete from the bucket folder is determined
        # by comparing the keys of the old and new asset file name map
        upload_keys = []
        delete_keys = []
        if self.statuses.get("transform"):
            upload_keys = [
                key
                for key in new_asset_file_name_map
                if key not in asset_file_name_map.keys()
            ]
            # also upload the XML file
            upload_keys.append(cleaner.article_xml_asset(asset_file_name_map)[0])
            delete_keys = [
                key
                for key in asset_file_name_map
                if key not in new_asset_file_name_map.keys()
            ]
        self.logger.info("%s, bucket objects to delete: %s" % (self.name, delete_keys))
        self.logger.info("%s, bucket objects to upload: %s" % (self.name, upload_keys))

        # delete files from bucket folder
        bucket_asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        for delete_key in delete_keys:
            s3_resource = bucket_asset_file_name_map.get(delete_key)
            # delete old key
            storage.delete_resource(s3_resource)
            self.logger.info("%s, deleted S3 object: %s" % (self.name, s3_resource))

        # upload files to bucket folder
        for upload_key in upload_keys:
            s3_resource = (
                self.settings.storage_provider
                + "://"
                + self.settings.bot_bucket
                + "/"
                + expanded_folder
                + "/"
                + upload_key
            )
            local_file_path = new_asset_file_name_map.get(upload_key)
            storage.set_resource_from_filename(s3_resource, local_file_path)
            self.logger.info(
                "%s, uploaded %s to S3 object: %s"
                % (self.name, local_file_path, s3_resource)
            )
            self.statuses["upload"] = True

        self.log_statuses(input_filename)

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


def download_code_files_from_bucket(
    storage, xml_file_path, asset_file_name_map, to_dir, logger
):
    "download files from the S3 bucket expanded folder to the local disk"
    code_files = cleaner.code_file_list(xml_file_path)
    cleaner.download_asset_files_from_bucket(
        storage, code_files, asset_file_name_map, to_dir, logger
    )
