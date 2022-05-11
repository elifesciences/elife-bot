import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from elifecleaner.transform import ArticleZipFile
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner
from activity.objects import Activity


REPAIR_XML = False


class activity_RenameAcceptedSubmissionVideos(Activity):
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

        # Track some values
        self.input_file = None
        self.activity_log_file = "cleaner.log"

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

        run = data["run"]
        session = get_session(self.settings, data, run)

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")
        article_id = session.get_value("article_id")
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
        log_file_path = os.path.join(
            self.get_tmp_dir(), self.activity_log_file
        )  # log file for this activity only
        cleaner_log_handers = cleaner.configure_activity_log_handlers(log_file_path)

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

        # get the file list from the XML
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
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

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
            try:
                cleaner.xml_rewrite_file_tags(
                    xml_file_path, file_transformations, input_filename
                )
                self.logger.info(
                    "%s, %s file_transformations rewriting XML completed"
                    % (self.name, input_filename)
                )
                self.statuses["modify_xml"] = True
            except:
                log_message = (
                    "%s, exception invoking xml_rewrite_file_tags for file %s"
                    % (
                        self.name,
                        input_filename,
                    )
                )
                self.logger.exception(log_message)

        # rename the video files in the expanded folder
        if self.statuses.get("modify_xml"):
            # map values without folder names to match them later
            asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}
            resource_prefix = (
                self.settings.storage_provider
                + "://"
                + self.settings.bot_bucket
                + "/"
                + expanded_folder
            )
            for file_transform in file_transformations:
                old_s3_resource = (
                    resource_prefix
                    + "/"
                    + asset_key_map.get(file_transform[0].xml_name)
                )
                # get the subfolder of the old resource to prepend to the new resource
                new_resource_subfolder = old_s3_resource.rsplit(resource_prefix, 1)[
                    -1
                ].rsplit("/", 1)[0]
                new_s3_resource = (
                    resource_prefix
                    + new_resource_subfolder
                    + "/"
                    + file_transform[1].xml_name
                )
                # copy old key to new key
                self.logger.info(
                    "%s, copying old S3 key %s to %s"
                    % (self.name, old_s3_resource, new_s3_resource)
                )
                storage.copy_resource(old_s3_resource, new_s3_resource)
                # delete old key
                self.logger.info(
                    "%s, deleting old S3 key %s" % (self.name, old_s3_resource)
                )
                storage.delete_resource(old_s3_resource)
            self.statuses["rename_videos"] = True

        # upload the modified XML file to the expanded folder
        if self.statuses.get("rename_videos"):
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
            local_file_path = asset_file_name_map.get(upload_key)
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
