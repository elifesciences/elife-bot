import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner
from activity.objects import Activity


REPAIR_XML = True


class activity_RepairAcceptedSubmission(Activity):
    "RepairAcceptedSubmission activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_RepairAcceptedSubmission, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "RepairAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download accepted submission XML from the bucket, repair it if required, "
            + "and replace it in the bucket."
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
        self.statuses = {"repair_xml": None, "output_xml": None, "upload_xml": None}

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

        # parse XML
        try:
            root = cleaner.parse_article_xml(xml_file_path)
            self.statuses["repair_xml"] = True
            self.logger.info("%s, %s XML root parsed" % (self.name, input_filename))
        except ParseError:
            log_message = "%s, XML ParseError exception parsing XML %s for file %s" % (
                self.name,
                xml_file_path,
                input_filename,
            )
            self.logger.exception(log_message)
            root = None
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        # write the repaired XML to disk
        if self.statuses.get("repair_xml"):
            local_file_path = os.path.join(
                self.directories.get("TEMP_DIR"),
                article_processing.file_name_from_name(xml_file_path),
            )
            cleaner.write_xml_file(root, local_file_path, input_filename)
            self.logger.info("%s, written XML to %s" % (self.name, local_file_path))
            self.statuses["output_xml"] = True

        # upload the XML to the bucket
        if self.statuses.get("output_xml"):
            upload_key = cleaner.article_xml_asset(asset_file_name_map)[0]
            s3_resource = (
                self.settings.storage_provider
                + "://"
                + self.settings.bot_bucket
                + "/"
                + expanded_folder
                + "/"
                + upload_key
            )
            storage.set_resource_from_filename(s3_resource, local_file_path)
            self.logger.info(
                "%s, uploaded %s to S3 object: %s"
                % (self.name, local_file_path, s3_resource)
            )
            self.statuses["upload_xml"] = True

        # remove the log handlers
        for log_handler in cleaner_log_handers:
            cleaner.log_remove_handler(log_handler)

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
