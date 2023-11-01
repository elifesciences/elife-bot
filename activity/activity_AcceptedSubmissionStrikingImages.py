import json
import os
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, utils
from activity.objects import AcceptedBaseActivity


class activity_AcceptedSubmissionStrikingImages(AcceptedBaseActivity):
    "AcceptedSubmissionStrikingImages activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionStrikingImages, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionStrikingImages"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Rename cover art images in the zip file and upload them to a bucket"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "images": None,
            "modify_xml": None,
            "rename_files": None,
            "upload_files": None,
        }

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        expanded_folder, input_filename, article_id = self.read_session(session)

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # find cover_art images
        cover_art_files = cleaner.cover_art_file_list(xml_file_path)
        self.logger.info("cover_art_files: %s" % cover_art_files)
        if not cover_art_files:
            self.logger.info(
                "%s, no cover_art files in %s" % (self.name, input_filename)
            )
            self.end_cleaner_log(session)
            return True
        self.statuses["images"] = True

        # rename the cover_art images

        xml_root = cleaner.parse_article_xml(xml_file_path)

        file_transformations = cleaner.cover_art_file_transformations(
            cover_art_files,
            asset_file_name_map,
            utils.pad_msid(article_id),
            input_filename,
        )
        self.logger.info(
            "%s, %s striking images file transformations for %s"
            % (len(file_transformations), self.name, input_filename)
        )
        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

        new_asset_file_name_map = cleaner.transform_cover_art_files(
            xml_file_path, asset_file_name_map, file_transformations, input_filename
        )
        self.statuses["modify_xml"] = True

        # rename the files in the expanded folder

        if self.statuses["modify_xml"]:
            self.logger.info(
                "%s, renaming striking images files in the expanded folder for %s"
                % (self.name, input_filename)
            )
            self.statuses["rename_files"] = self.rename_expanded_folder_files(
                asset_file_name_map, expanded_folder, file_transformations, storage
            )

        # upload the XML to the bucket
        self.upload_xml_file_to_bucket(asset_file_name_map, expanded_folder, storage)

        # copy the cover_art images to the striking images bucket
        if self.statuses["rename_files"]:
            self.logger.info(
                "%s, uploading files to the striking images bucket for %s"
                % (self.name, input_filename)
            )
            try:
                self.statuses["upload_files"] = self.copy_to_striking_image_bucket(
                    new_asset_file_name_map,
                    expanded_folder,
                    file_transformations,
                    article_id,
                    storage,
                )
            except Exception as exception:
                self.logger.exception(
                    "Exception copying files to the striking images bucket, input_filename %s: %s"
                    % (input_filename, str(exception))
                )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def copy_to_striking_image_bucket(
        self,
        asset_file_name_map,
        expanded_folder,
        file_transformations,
        article_id,
        storage,
    ):
        "rename objects in the S3 bucket expanded folder"
        # map values without folder names to match them later
        asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}
        old_resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        new_resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.striking_images_bucket
            + "/"
            + utils.pad_msid(article_id)
            + "/"
            + "vor"
        )
        for file_transform in file_transformations:
            old_s3_resource = (
                old_resource_prefix
                + "/"
                + asset_key_map.get(file_transform[1].xml_name)
            )
            new_s3_resource = new_resource_prefix + "/" + file_transform[1].xml_name
            # copy old key to new key
            self.logger.info(
                "%s, copying S3 key %s to %s"
                % (self.name, old_s3_resource, new_s3_resource)
            )
            storage.copy_resource(old_s3_resource, new_s3_resource)
        return True
