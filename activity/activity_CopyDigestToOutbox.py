import os
import json
import glob
from S3utility.s3_notification_info import parse_activity_data
from provider.storage_provider import storage_context
import provider.digest_provider as digest_provider
import provider.utils as utils
from .activity import Activity


"""
activity_CopyDigestToOutbox.py activity
"""


class activity_CopyDigestToOutbox(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_CopyDigestToOutbox, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "CopyDigestToOutbox"
        self.pretty_name = "Copy Digest files to an outbox"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Copies the Digest files to a bucket folder for later use" +
                            " in article ingestion")

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        # Download from S3
        input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)
        # Parse input and build digest
        build_status, digest = digest_provider.build_digest(
            input_file, self.temp_dir, self.logger)

        if not build_status:
            self.logger.info("Failed to build the Digest in Copy Digest To Outbox for %s",
                             real_filename)
            return self.ACTIVITY_PERMANENT_FAILURE

        # continue with copying files now

        # bucket name
        bucket_name = self.settings.bot_bucket

        # clean out the outbox if not empty
        self.clean_outbox(digest, bucket_name)

        # copy the files to S3
        # if it is zip file take the files from the temp_dir, otherwise from the input_dir
        from_dir = self.input_dir
        if input_file.endswith('.zip'):
            from_dir = self.temp_dir
        self.copy_files_to_outbox(digest, bucket_name, from_dir)

        return self.ACTIVITY_SUCCESS

    def dest_resource_path(self, digest, bucket_name):
        "the bucket folder where files will be saved"
        msid = utils.msid_from_doi(digest.doi)
        article_id = utils.pad_msid(msid)
        storage_provider = self.settings.storage_provider + "://"
        return storage_provider + bucket_name + "/digests/outbox/" + article_id + "/"

    def file_dest_resource(self, digest, bucket_name, file_path):
        "concatenate the S3 bucket object path we copy the file to"
        resource_path = self.dest_resource_path(digest, bucket_name)
        file_name = file_path.split(os.sep)[-1]
        new_file_name = digest_provider.new_file_name(
            msid=utils.msid_from_doi(digest.doi),
            file_name=file_name)
        dest_resource = resource_path + new_file_name
        return dest_resource

    def clean_outbox(self, digest, bucket_name):
        "remove files from the outbox folder"
        resource_path = self.dest_resource_path(digest, bucket_name)
        storage = storage_context(self.settings)
        files_in_bucket = storage.list_resources(resource_path)
        for resource in files_in_bucket:
            self.logger.info("Deleting %s from the outbox", resource)
            storage.delete_resource(resource)

    def copy_files_to_outbox(self, digest, bucket_name, from_dir):
        "copy all the files from the from_dir to the bucket"
        file_list = glob.glob(from_dir + "/*")
        storage = storage_context(self.settings)
        for file_path in file_list:
            resource_dest = self.file_dest_resource(digest, bucket_name, file_path)
            storage.set_resource_from_filename(resource_dest, file_path)
            self.logger.info("Copied %s to %s", file_path, resource_dest)

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
