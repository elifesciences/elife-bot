import os
import json
import traceback
from digestparser import build
from docx.opc.exceptions import PackageNotFoundError
from provider.storage_provider import storage_context
import provider.digest_provider as digest_provider
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
        real_filename, bucket_name, bucket_folder = digest_provider.parse_data(data)
        # Download from S3
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)
        # Parse input and build digest
        self.build_status, self.digest = self.build_digest(self.input_file)

        if not self.build_status:
            self.logger.info("Failed to build the Digest in Deposit Digest Ingest Assets for %s",
                             real_filename)
            return self.ACTIVITY_PERMANENT_FAILURE

        # check if there is an image and if not return True
        if not digest_provider.has_image(self.digest):
            self.logger.info("Digest for file %s has no images to deposit",
                             real_filename)
            return self.ACTIVITY_SUCCESS

        # deposit the image file to S3
        self.deposit_digest_image(self.digest)

        return self.ACTIVITY_SUCCESS

    def build_digest(self, input_file):
        "Parse input and build a Digest object"
        if not input_file:
            return False, None
        try:
            digest = build.build_digest(input_file, self.temp_dir)
        except PackageNotFoundError:
            # bad docx file
            if self.logger:
                self.logger.exception('exception in DepositDigestIngestAssets build_digest: %s' %
                                      traceback.format_exc())
            return False, None
        return True, digest

    def deposit_digest_image(self, digest):
        "deposit the image file from the digest to the bucket"
        # todo!!!
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
