import os
import json
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
        self.description = "Copies the Digest files to a bucket folder for later use"

        # Track some values
        self.input_file = None
        self.digest = None

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
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)
        # Parse input and build digest
        self.build_status, self.digest = digest_provider.build_digest(
            self.input_file, self.temp_dir, self.logger)

        if not self.build_status:
            self.logger.info("Failed to build the Digest in Copy Digest To Outbox for %s",
                             real_filename)
            return self.ACTIVITY_PERMANENT_FAILURE

        # todo!!  the rest of the logic

        return self.ACTIVITY_SUCCESS

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
