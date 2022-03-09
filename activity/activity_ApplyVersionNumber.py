import json
import os
import re
from os import path
from elifetools import xmlio
from provider.execution_context import get_session
from provider.article_structure import ArticleInfo
import provider.article_structure as article_structure
from provider.storage_provider import storage_context
from activity.objects import Activity

"""
ApplyVersionNumber.py activity
"""


class activity_ApplyVersionNumber(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ApplyVersionNumber, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ApplyVersionNumber"
        self.pretty_name = "Apply Version Number"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Rename expanded article files on S3 with a new version number"
        )
        self.logger = logger

    def do_activity(self, data=None):

        try:

            self.expanded_bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
            )

            run = data["run"]
            session = get_session(self.settings, data, run)
            version = session.get_value("version")
            article_id = session.get_value("article_id")

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "start",
                "Starting applying version number to files for " + article_id,
            )
        except Exception as exception:
            self.logger.exception(str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        try:

            if self.logger:
                self.logger.info(
                    "data: %s" % json.dumps(data, sort_keys=True, indent=4)
                )

            if version is None:
                self.emit_monitor_event(
                    self.settings,
                    article_id,
                    version,
                    run,
                    self.pretty_name,
                    "error",
                    "Error in applying version number to files for "
                    + article_id
                    + " message: No version available",
                )
                return self.ACTIVITY_PERMANENT_FAILURE

            expanded_folder_name = session.get_value("expanded_folder")
            bucket_folder_name = expanded_folder_name.replace(os.sep, "/")
            self.rename_article_s3_objects(bucket_folder_name, version)

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                "Finished applying version number to article "
                + article_id
                + " for version "
                + version
                + " run "
                + str(run),
            )

        except Exception as exception:
            self.logger.exception(str(exception))
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error in applying version number to files for "
                + article_id
                + " message:"
                + str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        return self.ACTIVITY_SUCCESS

    def rename_article_s3_objects(self, bucket_folder_name, version):
        """
        Main function to rename article objects on S3
        and apply the renamed file names to the article XML file
        """

        storage = storage_context(self.settings)
        bucket_resource = (
            self.settings.storage_provider
            + "://"
            + self.expanded_bucket_name
            + "/"
            + bucket_folder_name
        )

        # bucket object list
        s3_key_names = storage.list_resources(bucket_resource)

        # Get the old name to new name map
        file_name_map = self.build_file_name_map(s3_key_names, version)

        # log file names for reference
        if self.logger:
            self.logger.info(
                "file_name_map: %s"
                % json.dumps(file_name_map, sort_keys=True, indent=4)
            )

        # rename_s3_objects(old_name_new_name_dict)
        self.rename_s3_objects(
            self.expanded_bucket_name, bucket_folder_name, file_name_map
        )

        # rewrite_and_upload_article_xml()
        xml_filename = find_xml_filename_in_map(file_name_map)
        self.download_file_from_bucket(
            self.expanded_bucket_name, bucket_folder_name, xml_filename
        )
        self.rewrite_xml_file(xml_filename, file_name_map)
        self.upload_file_to_bucket(
            self.expanded_bucket_name, bucket_folder_name, xml_filename
        )

    def download_file_from_bucket(self, bucket_name, bucket_folder_name, filename):
        storage = storage_context(self.settings)
        file_resource_origin = (
            self.settings.storage_provider
            + "://"
            + bucket_name
            + "/"
            + bucket_folder_name
            + "/"
            + filename
        )
        local_filename = path.join(self.get_tmp_dir(), filename)
        with open(local_filename, "wb") as open_file:
            storage.get_resource_to_file(file_resource_origin, open_file)

    def rewrite_xml_file(self, xml_filename, file_name_map):

        local_xml_filename = path.join(self.get_tmp_dir(), xml_filename)

        xmlio.register_xmlns()
        root, doctype_dict, processing_instructions = xmlio.parse(
            local_xml_filename,
            return_doctype_dict=True,
            return_processing_instructions=True,
        )

        # Convert xlink href values
        total = xmlio.convert_xlink_href(root, file_name_map)

        # Start the file output
        reparsed_string = xmlio.output(
            root,
            output_type=None,
            doctype_dict=doctype_dict,
            processing_instructions=processing_instructions,
        )
        with open(local_xml_filename, "wb") as open_file:
            open_file.write(reparsed_string)

    def upload_file_to_bucket(self, bucket_name, bucket_folder_name, filename):
        storage = storage_context(self.settings)
        file_resource = (
            self.settings.storage_provider
            + "://"
            + bucket_name
            + "/"
            + bucket_folder_name
            + "/"
            + filename
        )
        local_filename = path.join(self.get_tmp_dir(), filename)
        storage.set_resource_from_filename(file_resource, local_filename)

    def build_file_name_map(self, s3_key_names, version):

        file_name_map = {}

        for key_name in s3_key_names:
            filename = key_name.split("/")[-1]

            # Get the new file name
            file_name_map[filename] = None

            if article_structure.is_video_file(filename) is False:
                renamed_filename = new_filename(filename, version)
            else:
                # Keep video files named the same
                renamed_filename = filename

            if renamed_filename:
                file_name_map[filename] = renamed_filename
            else:
                if self.logger:
                    self.logger.info("there is no renamed file for " + filename)

        return file_name_map

    def rename_s3_objects(self, bucket_name, bucket_folder_name, file_name_map):
        # Rename S3 bucket objects by copying them and then deleting the old objects
        storage = storage_context(self.settings)
        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + bucket_name
            + "/"
            + bucket_folder_name
        )
        for old_name, new_name in list(file_name_map.items()):
            # Do not need to rename if the old and new name are the same
            if old_name == new_name:
                continue

            if new_name is not None:
                old_s3_resource = resource_prefix + "/" + old_name
                new_s3_resource = resource_prefix + "/" + new_name

                # copy old key to new key
                storage.copy_resource(old_s3_resource, new_s3_resource)
                # delete old key
                storage.delete_resource(old_s3_resource)


def new_filename(old_filename, version):
    if re.search(r"-v([0-9])[\.]", old_filename):  # is version already in file name?
        new_filename = re.sub(r"-v([0-9])[\.]", "-v" + str(version) + ".", old_filename)
    else:
        (file_prefix, file_extension) = article_structure.file_parts(old_filename)
        new_filename = file_prefix + "-v" + str(version) + "." + file_extension
    return new_filename


def find_xml_filename_in_map(file_name_map):
    for old_name, new_name in list(file_name_map.items()):
        info = ArticleInfo(new_name)
        if info.file_type == "ArticleXML":
            return new_name
    return None
