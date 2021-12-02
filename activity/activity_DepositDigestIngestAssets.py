import os
import json
from S3utility.s3_notification_info import parse_activity_data
from provider.storage_provider import storage_context
from provider import digest_provider, download_helper
import provider.utils as utils
from activity.objects import Activity

"""
DepositDigestIngestAssets.py activity
"""


class activity_DepositDigestIngestAssets(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositDigestIngestAssets, self).__init__(
            settings, logger, conn, token, activity_task
        )

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
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.build_status = None

    def do_activity(self, data=None):
        "do the work"
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
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
        self.build_status, self.digest = digest_provider.build_digest(
            self.input_file,
            self.directories.get("TEMP_DIR"),
            self.logger,
            digest_config,
        )

        if not self.build_status:
            self.logger.info(
                "Failed to build the Digest in Deposit Digest Ingest Assets for %s",
                real_filename,
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # check if there is an image and if not return True
        if not digest_provider.has_image(self.digest):
            self.logger.info(
                "Digest for file %s has no images to deposit", real_filename
            )
            return self.ACTIVITY_SUCCESS

        # bucket name
        cdn_bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.digest_cdn_bucket
        )

        # deposit the image file to S3
        self.deposit_digest_image(self.digest, cdn_bucket_name)

        return self.ACTIVITY_SUCCESS

    def image_dest_resource(self, digest, cdn_bucket_name):
        "concatenate the S3 bucket object path we copy the file to"
        msid = utils.msid_from_doi(digest.doi)
        article_id = utils.pad_msid(msid)
        # file name from the digest image file
        file_name = digest.image.file.split(os.sep)[-1]
        new_file_name = digest_provider.new_file_name(file_name, msid)
        storage_provider = self.settings.storage_provider + "://"
        dest_resource = (
            storage_provider + cdn_bucket_name + "/" + article_id + "/" + new_file_name
        )
        return dest_resource

    def deposit_digest_image(self, digest, cdn_bucket_name):
        "deposit the image file from the digest to the bucket"
        self.dest_resource = self.image_dest_resource(digest, cdn_bucket_name)
        storage = storage_context(self.settings)
        self.logger.info("Depositing digest image to S3 key %s", self.dest_resource)
        # set the bucket object resource from the local file
        storage.set_resource_from_filename(self.dest_resource, digest.image.file)
        self.logger.info("Deposited digest image %s to S3", digest.image.file)
        return True
