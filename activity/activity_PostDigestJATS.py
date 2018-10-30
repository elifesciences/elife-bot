import os
import json
from S3utility.s3_notification_info import parse_activity_data
import provider.digest_provider as digest_provider
from .activity import Activity


class activity_PostDigestJATS(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PostDigestJATS, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PostDigestJATS"
        self.pretty_name = "POST Digest JATS content to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("POST Digest JATS content to API endpoint," +
                            " to be run when a digest package is first ingested")

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

        # Track the success of some steps
        self.statuses = {
            "build": None,
            "jats": None,
            "post": None
        }

        # Track some values
        self.input_file = None
        self.digest = None
        self.jats_content = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section,
            self.settings.digest_config_file)

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)

        # Parse input and build digest
        self.statuses["build"], self.digest = digest_provider.build_digest(
            self.input_file, self.temp_dir, self.logger, self.digest_config)

        # Generate jats
        self.jats_content = self.digest_jats(self.input_file)

        if self.jats_content:
            self.statuses["jats"] = True

        # TODO!!! POST to API endpoint
        try:
            self.statuses["post"] = True
        except Exception as exception:
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))

        self.logger.info(
            "%s for real_filename %s statuses: %s" % (self.name, str(real_filename), self.statuses))

        if self.statuses.get("jats"):
            return self.ACTIVITY_SUCCESS

        return self.ACTIVITY_PERMANENT_FAILURE

    def digest_jats(self, docx_file):
        "generate the digest JATS content from the docx file"
        try:
            return digest_provider.build_jats(docx_file, self.temp_dir, self.digest_config)
        except Exception as exception:
            self.logger.exception(
                "Exception generating digest jats for docx_file %s. Details: %s" %
                (str(docx_file), str(exception)))

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
