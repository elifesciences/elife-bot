import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner
from activity.objects import AcceptedBaseActivity


class activity_RepairAcceptedSubmission(AcceptedBaseActivity):
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

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

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

        # write the repaired XML to disk
        if self.statuses.get("repair_xml"):
            local_file_path = os.path.join(
                self.directories.get("TEMP_DIR"),
                article_processing.file_name_from_name(xml_file_path),
            )
            cleaner.write_xml_file(root, local_file_path, input_filename)
            # set the XML file path in the asset file name map
            asset_file_name_map[
                cleaner.article_xml_asset(asset_file_name_map)[0]
            ] = local_file_path
            self.logger.info("%s, written XML to %s" % (self.name, local_file_path))
            self.statuses["output_xml"] = True

        # upload the XML to the bucket
        if self.statuses.get("output_xml"):
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True
