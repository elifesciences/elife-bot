import os
import json
import time
from S3utility.s3_notification_info import parse_activity_data
from provider import download_helper, email_provider, letterparser_provider
from activity.objects import Activity


class activity_ValidateDecisionLetterInput(Activity):
    "ValidateDecisionLetter activity"
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ValidateDecisionLetterInput, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "ValidateDecisionLetterInput"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Download decision letter zip file from the bucket, parse it, " +
                            "check for valid data, and raise an error if it is invalid.")

        # Track some values
        self.input_file = None
        self.articles = None
        self.root = None
        self.xml_string = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        # Track the success of some steps
        self.statuses = {
            "unzip": None,
            "build": None,
            "valid": None,
            "generate": None,
            "output": None,
            "email": None
        }

        # Load the config
        self.letterparser_config = letterparser_provider.letterparser_config(self.settings)

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # parse the activity data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder,
            self.directories.get("INPUT_DIR"))

        # Unzip file
        self.statuses["unzip"], docx_file_name, asset_file_names = letterparser_provider.unzip_zip(
            self.input_file, self.directories.get("TEMP_DIR"), logger=self.logger)

        # Convert docx to articles
        self.statuses["build"], self.articles = letterparser_provider.docx_to_articles(
            docx_file_name, config=self.letterparser_config, logger=self.logger)

        # Validate content of articles
        self.statuses["valid"], error_messages = letterparser_provider.validate_articles(
            self.articles, logger=self.logger)

        # Generate XML from articles
        self.statuses["generate"], self.root = letterparser_provider.generate_root(
            self.articles, temp_dir=self.directories.get("TEMP_DIR"), logger=self.logger)

        # Output XML
        self.statuses["output"], self.xml_string = letterparser_provider.output_xml(
            self.root, pretty=True, indent="   ", logger=self.logger)

        # Additional error messages
        if not self.statuses.get("unzip"):
            error_messages.append("Unable to unzip decision letter")

        if not self.statuses.get("valid") or not self.statuses.get("output"):
            # Send error email
            self.statuses["email"] = self.email_error_report(real_filename, error_messages)
            self.log_statuses(self.input_file)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.log_statuses(self.input_file)
        return True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s" % (self.name, str(input_file), self.statuses))

    def email_error_report(self, filename, error_messages):
        "send an email on error"
        datetime_string = time.strftime('%Y-%m-%d %H:%M', time.gmtime())
        body = email_provider.simple_email_body(datetime_string, error_messages)
        subject = error_email_subject(filename)
        sender_email = self.settings.decision_letter_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.decision_letter_validate_error_recipient_email)

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_provider.smtp_send(connection, sender_email, recipient,
                                     email_message, self.logger)
        return True


def error_email_subject(filename):
    "email subject for an error email"
    return u'Error processing decision letter file: {filename}'.format(filename=filename)
