import json
import os
from provider import cleaner, outbox_provider
from provider.execution_context import get_session
from activity.objects import Activity


class activity_ScheduleCrossrefPendingPublication(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ScheduleCrossrefPendingPublication, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ScheduleCrossrefPendingPublication"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue the article XML for depositing as a "
            "pending publication DOI to Crossref."
        )
        self.logger = logger
        self.pretty_name = "Schedule Crossref Pending Publication"

        # Track some values
        self.input_file = None

        # For copying to S3 bucket outbox
        self.crossref_outbox_folder = outbox_provider.outbox_folder(
            "crossref_pending_publication"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):

        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        run = data["run"]
        session = get_session(self.settings, data, run)

        expanded_folder = session.get_value("expanded_folder")
        self.logger.info("%s, expanded_folder: %s" % (self.name, expanded_folder))

        # get list of bucket objects from expanded folder
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )

        # find S3 object for article XML and download it
        xml_file_path = cleaner.download_xml_file_from_bucket(
            self.settings,
            asset_file_name_map,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )

        self.logger.info("%s, downloaded XML file to %s" % (self.name, xml_file_path))

        # upload to the outbox folder
        outbox_provider.upload_files_to_s3_folder(
            self.settings,
            self.settings.poa_packaging_bucket,
            self.crossref_outbox_folder,
            [xml_file_path],
        )

        self.logger.info(
            ("%s, uploaded %s to S3 bucket %s, folder %s")
            % (
                self.name,
                xml_file_path,
                self.settings.poa_packaging_bucket,
                self.crossref_outbox_folder,
            )
        )

        # Clean up disk
        self.clean_tmp_dir()

        return True
