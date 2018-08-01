import os
import json
from provider.storage_provider import storage_context
from S3utility.s3_notification_info import parse_activity_data
import provider.digest_provider as digest_provider
import provider.utils as utils
from .activity import Activity

"""
DepositDigestIngestAssets.py activity
"""


class activity_DepositDigestIngestAssets(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositDigestIngestAssets, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "DepositDigestIngestAssets"
        self.pretty_name = "Deposit Digest Ingest Assets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit Assets for a Digest (Pre-Ingest)"

        # Track some values
        self.input_file = None
        self.digest = None
        self.dest_resource = None

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

        # Track the success of some steps
        self.build_status = None

    def do_activity(self, data=None):
        "do the work"
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        # Download from S3
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)
        # Parse input and build digest
        self.build_status, self.digest = digest_provider.build_digest(
            self.input_file, self.temp_dir, self.logger)

        if not self.build_status:
            self.logger.info("Failed to build the Digest in Deposit Digest Ingest Assets for %s",
                             real_filename)
            return self.ACTIVITY_PERMANENT_FAILURE

        # check if there is an image and if not return True
        if not digest_provider.has_image(self.digest):
            self.logger.info("Digest for file %s has no images to deposit",
                             real_filename)
            return self.ACTIVITY_SUCCESS

        # bucket name
        cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.digest_cdn_bucket

        # deposit the image file to S3
        self.deposit_digest_image(self.digest, cdn_bucket_name)

        return self.ACTIVITY_SUCCESS

    def image_dest_resource(self, digest, cdn_bucket_name):
        "concatenate the S3 bucket object path we copy the file to"
        msid = utils.msid_from_doi(digest.doi)
        article_id = utils.pad_msid(msid)
        # file name from the digest image file
        file_name = digest.image.file.split(os.sep)[-1]
        storage_provider = self.settings.storage_provider + "://"
        dest_resource = storage_provider + cdn_bucket_name + "/" + article_id + "/" + file_name
        return dest_resource

    def deposit_digest_image(self, digest, cdn_bucket_name):
        "deposit the image file from the digest to the bucket"
        self.dest_resource = self.image_dest_resource(digest, cdn_bucket_name)
        storage = storage_context(self.settings)
        self.logger.info("Depositing digest image to S3 key %s",
                         self.dest_resource)
        # set the bucket object resource from the local file
        storage.set_resource_from_filename(self.dest_resource, digest.image.file)
        self.logger.info("Deposited digest image %s to S3",
                         digest.image.file)
        return True

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
