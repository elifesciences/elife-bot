import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from S3utility.s3_notification_info import parse_activity_data
from provider import cleaner, download_helper, email_provider, utils
from activity.objects import Activity


REPAIR_XML = False


class activity_ValidateAcceptedSubmission(Activity):
    "ValidateAcceptedSubmission activity"

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ValidateAcceptedSubmission, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "ValidateAcceptedSubmission"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download zip file input from the bucket, parse it, check contents "
            + "and log warning or error messages."
        )

        # Track some values
        self.input_file = None
        self.activity_log_file = "cleaner.log"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"valid": None, "email": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # configure log files for the cleaner provider
        cleaner_log_handers = []
        format_string = (
            "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
        )
        # log to a common log file
        cleaner_log_handers.append(cleaner.log_to_file(format_string=format_string))
        # log file for this activity only
        log_file_path = os.path.join(self.get_tmp_dir(), self.activity_log_file)
        cleaner_log_handers.append(
            cleaner.log_to_file(
                log_file_path,
                format_string=format_string,
            )
        )

        # parse the input data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        self.logger.info(
            "%s, real_filename: %s, bucket_name: %s, bucket_folder: %s"
            % (self.name, real_filename, bucket_name, bucket_folder)
        )

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )

        self.logger.info("%s, downloaded file to %s" % (self.name, self.input_file))

        # unzip the file and validate
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML
        try:
            self.statuses["valid"] = cleaner.check_ejp_zip(
                self.input_file, self.directories.get("TEMP_DIR")
            )
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.check_ejp_zip for file %s"
                % (self.name, self.input_file)
            )
            self.logger.exception(log_message)
            # Send error email
            self.statuses["email"] = self.email_error_report(real_filename, log_message)
            self.log_statuses(self.input_file)
        except Exception:
            log_message = (
                "%s, unhandled exception in cleaner.check_ejp_zip for file %s"
                % (self.name, self.input_file)
            )
            self.logger.exception(log_message)
            # Send error email
            self.statuses["email"] = self.email_error_report(real_filename, log_message)
            self.log_statuses(self.input_file)
            return self.ACTIVITY_PERMANENT_FAILURE
        finally:
            # remove the log handlers
            for log_handler in cleaner_log_handers:
                cleaner.log_remove_handler(log_handler)
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        # Send an email if the log has warnings
        log_contents = ""
        with open(log_file_path, "r") as open_file:
            log_contents = open_file.read()
        if "WARNING" in log_contents:
            # Send error email
            error_messages = (
                "Warnings found in the log file for zip file %s\n\n" % real_filename
            )
            error_messages += log_contents
            self.statuses["email"] = self.email_error_report(
                real_filename, error_messages
            )

        self.log_statuses(self.input_file)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )

    def clean_tmp_dir(self):
        "custom cleaning of temp directory in order to retain some files for debugging purposes"
        keep_dirs = []
        for dir_name, dir_path in self.directories.items():
            if dir_name in keep_dirs or not os.path.exists(dir_path):
                continue
            shutil.rmtree(dir_path)

    def email_error_report(self, filename, error_messages):
        "send an email on error"
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        body = email_provider.simple_email_body(datetime_string, error_messages)
        subject = error_email_subject(filename)
        sender_email = self.settings.accepted_submission_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.accepted_submission_validate_error_recipient_email
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
    return u"Error validating accepted submission file: {filename}".format(
        filename=filename
    )
