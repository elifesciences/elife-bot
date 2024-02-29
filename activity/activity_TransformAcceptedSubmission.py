import os
import json
import shutil
from xml.etree.ElementTree import ParseError
from provider import article_processing, cleaner
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import AcceptedBaseActivity


class activity_TransformAcceptedSubmission(AcceptedBaseActivity):
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

        # PRC XML changes
        if session.get_value("prc_status"):
            cleaner.transform_prc(xml_file_path, input_filename)
            docmap_string = cleaner.get_docmap_string(
                self.settings, article_id, input_filename, self.name, self.logger
            )
            # set the volume tag value
            self.set_volume_tag(
                article_id, xml_file_path, input_filename, docmap_string
            )
            # set the elocation-id tag value
            self.set_elocation_id_tag(
                article_id, xml_file_path, input_filename, docmap_string
            )

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
                self.end_cleaner_log(session)

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

    def set_volume_tag(self, article_id, xml_file_path, input_filename, docmap_string):
        "from the docmap calculate the volume value and set the volume XML tag text"
        # get volume from the docmap
        volume = cleaner.volume_from_docmap(docmap_string, input_filename)
        self.logger.info(
            "%s, from article %s docmap got volume value: %s",
            self.name,
            article_id,
            volume,
        )
        if volume:
            # modify the volume tag text
            root = cleaner.parse_article_xml(xml_file_path)
            volume_tag = root.find("front/article-meta/volume")
            if volume_tag is not None:
                volume_tag.text = str(volume)
                cleaner.write_xml_file(root, xml_file_path, input_filename)
            else:
                self.logger.info(
                    "%s, no volume XML tag found for article %s",
                    self.name,
                    article_id,
                )

    def set_elocation_id_tag(
        self, article_id, xml_file_path, input_filename, docmap_string
    ):
        "from the docmap get the elocation-id value and set the elocation-id XML tag text"
        # get volume from the docmap
        elocation_id = cleaner.elocation_id_from_docmap(docmap_string, input_filename)
        self.logger.info(
            "%s, from article %s docmap got elocation_id value: %s",
            self.name,
            article_id,
            elocation_id,
        )
        if elocation_id:
            # modify the volume tag text
            root = cleaner.parse_article_xml(xml_file_path)
            elocation_id_tag = root.find("front/article-meta/elocation-id")
            if elocation_id_tag is not None:
                elocation_id_tag.text = elocation_id
                cleaner.write_xml_file(root, xml_file_path, input_filename)
            else:
                self.logger.info(
                    "%s, no elocation-id XML tag found for article %s",
                    self.name,
                    article_id,
                )


def download_code_files_from_bucket(
    storage, xml_file_path, asset_file_name_map, to_dir, logger
):
    "download files from the S3 bucket expanded folder to the local disk"
    code_files = cleaner.code_file_list(xml_file_path)
    cleaner.download_asset_files_from_bucket(
        storage, code_files, asset_file_name_map, to_dir, logger
    )
