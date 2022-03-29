import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider import cleaner, glencoe_check
from activity.objects import Activity


REPAIR_XML = False


class activity_ValidateAcceptedSubmissionVideos(Activity):
    "ValidateAcceptedSubmissionVideos activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidateAcceptedSubmissionVideos, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ValidateAcceptedSubmissionVideos"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Check accepted submission videos for whether they should be processed "
            + "and deposited to a video service as part of the ingestion workflow."
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
        self.statuses = {"valid": None, "deposit_videos": None}

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

        # configure log files for the cleaner provider
        log_file_path = os.path.join(
            self.get_tmp_dir(), self.activity_log_file
        )  # log file for this activity only
        cleaner_log_handers = cleaner.configure_activity_log_handlers(log_file_path)

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")
        article_id = session.get_value("article_id")

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
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # get list of files from the article XML
        files = []
        try:
            files = cleaner.file_list(xml_file_path)
            self.logger.info("%s, %s files: %s" % (self.name, input_filename, files))
        except ParseError:
            log_message = "%s, XML ParseError exception parsing file %s for file %s" % (
                self.name,
                xml_file_path,
                input_filename,
            )
            self.logger.exception(log_message)
            self.log_statuses(input_filename)
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        ###### start validation checks

        # check if there are any video files in the XML
        video_files = [
            file_data for file_data in files if file_data.get("file_type") == "video"
        ]

        # todo!!! add more validation checks to video files as applicable
        self.logger.info(
            "%s, %s video_files: %s" % (self.name, input_filename, video_files)
        )
        if video_files:
            self.statuses["valid"] = True

        # check for existing video metadata if there are videos
        if self.statuses["valid"]:
            no_video_metadata = None
            try:
                gc_data = glencoe_check.metadata(
                    glencoe_check.check_msid(article_id), self.settings
                )
                self.logger.info(
                    "%s, %s gc_data: %s"
                    % (self.name, article_id, json.dumps(gc_data, indent=4))
                )
                no_video_metadata = False
            except AssertionError as exception:
                if str(exception).startswith("article has no videos"):
                    self.logger.info(
                        "%s, %s has no video metadata" % (self.name, article_id)
                    )
                    no_video_metadata = True

            # deposit the videos later only if there is no metadata already available
            self.statuses["deposit_videos"] = no_video_metadata

        # set session value
        if self.statuses["deposit_videos"] is not None:
            session.store_value("deposit_videos", self.statuses["deposit_videos"])

        ###### end of validation checks

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
