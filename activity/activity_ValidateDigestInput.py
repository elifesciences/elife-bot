import os
import json
import time
from S3utility.s3_notification_info import parse_activity_data
from provider import digest_provider, download_helper, email_provider, utils
from activity.objects import Activity


class activity_ValidateDigestInput(Activity):
    "ValidateDigestInput activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidateDigestInput, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ValidateDigestInput"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download digest file input from the bucket, parse it, check for "
            + "valid data, and raise an error if it is invalid."
        )

        # Track some values
        self.input_file = None
        self.digest = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"build": None, "valid": None, "email": None}

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

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
        self.statuses["build"], self.digest = digest_provider.build_digest(
            self.input_file,
            self.directories.get("TEMP_DIR"),
            self.logger,
            self.digest_config,
        )

        # Approve files for emailing
        self.statuses["valid"], error_messages = digest_provider.validate_digest(
            self.digest
        )

        if not self.statuses.get("build") or not self.statuses.get("valid"):
            # Send error email
            self.statuses["email"] = self.email_error_report(
                real_filename, error_messages
            )
            self.log_statuses(self.input_file)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.log_statuses(self.input_file)
        return True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )

    def email_error_report(self, filename, error_messages):
        "send an email on error"
        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string, error_messages)
        subject = error_email_subject(filename)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_validate_error_recipient_email
        )

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_provider.smtp_send(
                connection, sender_email, recipient, email_message, self.logger
            )
        return True


def error_email_subject(filename):
    "email subject for an error email"
    return u"Error processing digest file: {filename}".format(filename=filename)
