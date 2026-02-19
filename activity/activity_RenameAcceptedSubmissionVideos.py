import os
import json
from xml.etree.ElementTree import ParseError
from elifecleaner.transform import ArticleZipFile
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner
from activity.objects import AcceptedBaseActivity


class activity_RenameAcceptedSubmissionVideos(AcceptedBaseActivity):
    "RenameAcceptedSubmissionVideos activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_RenameAcceptedSubmissionVideos, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "RenameAcceptedSubmissionVideos"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Rename the accepted submission videos in the bucket folder"
            " and in the XML file."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"rename_videos": None, "modify_xml": None, "upload_xml": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)
        resource_prefix = self.accepted_expanded_resource_prefix(expanded_folder)

        deposit_videos = session.get_value("deposit_videos")

        if not deposit_videos:
            self.logger.info(
                "%s, %s deposit_videos session value is %s, activity returning True"
                % (self.name, input_filename, deposit_videos)
            )
            return True

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

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

        # generate new file names for the videos
        generated_video_data = []
        try:
            generated_video_data = cleaner.video_data_from_files(files, article_id)
        except ParseError:
            log_message = "%s, exception invoking video_data_from_files for file %s" % (
                self.name,
                input_filename,
            )
            self.logger.exception(log_message)
        file_transformations = []
        for video_data in generated_video_data:
            from_file_name = video_data.get("upload_file_nm")
            from_file = ArticleZipFile(from_file_name)
            to_file_name = video_data.get("video_filename")
            to_file = ArticleZipFile(to_file_name)
            file_transformations.append((from_file, to_file))
        self.logger.info(
            "%s, %s file_transformations: %s"
            % (self.name, input_filename, file_transformations)
        )

        # rewrite the XML file with the renamed video files
        if file_transformations:
            self.statuses["modify_xml"] = self.rewrite_file_tags(
                xml_file_path, file_transformations, input_filename
            )

        # rename the video files in the expanded folder
        if self.statuses.get("modify_xml"):
            self.statuses["rename_videos"] = self.rename_expanded_folder_files(
                asset_file_name_map, resource_prefix, file_transformations, storage
            )

        # upload the modified XML file to the expanded folder
        if self.statuses.get("rename_videos"):
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True
