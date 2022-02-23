import os
import json
from S3utility.s3_notification_info import parse_activity_data
from provider.storage_provider import storage_context
from provider.utils import unicode_encode
from provider import digest_provider, download_helper
from activity.objects import Activity


"""
activity_CopyDigestToOutbox.py activity
"""


class activity_CopyDigestToOutbox(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_CopyDigestToOutbox, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "CopyDigestToOutbox"
        self.pretty_name = "Copy Digest files to an outbox"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Copies the Digest files to a bucket folder for later use"
            + " in article ingestion"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        # Download from S3
        input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )
        # Parse input and build digest
        digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )
        build_status, digest = digest_provider.build_digest(
            input_file, self.directories.get("TEMP_DIR"), self.logger, digest_config
        )

        if not build_status:
            self.logger.info(
                "Failed to build the Digest in Copy Digest To Outbox for %s",
                real_filename,
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # continue with copying files now

        # bucket name
        bucket_name = self.settings.bot_bucket

        # clean out the outbox if not empty
        self.clean_outbox(digest, bucket_name)

        # copy the files to S3
        # if it is zip file take the files from the temp_dir, otherwise from the input_dir
        from_dir = self.directories.get("INPUT_DIR")
        if input_file.endswith(".zip"):
            from_dir = self.directories.get("TEMP_DIR")
        self.copy_files_to_outbox(digest, bucket_name, from_dir)

        return self.ACTIVITY_SUCCESS

    def clean_outbox(self, digest, bucket_name):
        "remove files from the outbox folder"
        resource_path = digest_provider.outbox_dest_resource_path(
            self.settings.storage_provider, digest, bucket_name
        )
        storage = storage_context(self.settings)
        files_in_bucket = storage.list_resources(resource_path)
        # remove the subfolder name from file names
        files_in_bucket = [filename.rsplit("/", 1)[-1] for filename in files_in_bucket]
        for resource in files_in_bucket:
            orig_resource = resource_path + "/" + resource
            self.logger.info("Deleting %s from the outbox", orig_resource)
            storage.delete_resource(orig_resource)

    def copy_files_to_outbox(self, digest, bucket_name, from_dir):
        "copy all the files from the from_dir to the bucket"
        storage = storage_context(self.settings)
        self.logger.info("from_dir type: %s" % type(from_dir))
        encoded_from_dir = unicode_encode(from_dir)
        self.logger.info("encoded_from_dir type: %s" % type(encoded_from_dir))
        file_list = os.listdir(from_dir)
        for file_name in file_list:
            self.logger.info("file_name type: %s" % type(file_name))
            encoded_file_name = unicode_encode(file_name)
            self.logger.info("encoded_file_name type: %s" % type(encoded_file_name))
            file_path = os.path.join(encoded_from_dir, encoded_file_name)
            self.logger.info("file_path: %s" % file_path)
            resource_dest = digest_provider.outbox_file_dest_resource(
                self.settings.storage_provider, digest, bucket_name, file_path
            )
            self.logger.info("Copying %s to %s", file_path, resource_dest)
            storage.set_resource_from_filename(resource_dest, file_path)
