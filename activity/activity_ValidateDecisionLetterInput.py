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

        # part 1 zip file to articles and assets
        self.articles, asset_file_names, statuses, error_messages = (
            letterparser_provider.process_zip(
                self.input_file,
                config=self.letterparser_config,
                temp_dir=self.directories.get("TEMP_DIR"),
                logger=self.logger))

        self.set_statuses(statuses)

        # part 2 articles to XML
        self.xml_string, statuses = letterparser_provider.process_articles_to_xml(
            self.articles,
            self.directories.get("TEMP_DIR"),
            self.logger,
            pretty=True,
            indent="")

        self.set_statuses(statuses)

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

    def set_statuses(self, statuses):
        """copy statuses values to self.statuses"""
        for status, value in statuses.items():
            self.statuses[status] = value

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
