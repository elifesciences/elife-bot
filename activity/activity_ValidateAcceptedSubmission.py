import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner, email_provider
from activity.objects import Activity


REPAIR_XML = False


class activity_ValidateAcceptedSubmission(Activity):
    "ValidateAcceptedSubmission activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidateAcceptedSubmission, self).__init__(
            settings, logger, client, token, activity_task
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

        run = data["run"]
        session = get_session(self.settings, data, run)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        log_file_path = os.path.join(
            self.get_tmp_dir(), self.activity_log_file
        )  # log file for this activity only
        cleaner_log_handers = cleaner.configure_activity_log_handlers(log_file_path)

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # get list of bucket objects from expanded folder
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        self.logger.info(
            "%s, asset_file_name_map: %s" % (self.name, asset_file_name_map)
        )

        # find S3 object for article XML and download it
        xml_file_path = cleaner.download_xml_file_from_bucket(
            self.settings,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # get list of files from the article XML
        try:
            files = cleaner.file_list(xml_file_path)
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.file_list"
                " parsing XML file %s for file %s"
            ) % (
                self.name,
                article_processing.file_name_from_name(xml_file_path),
                input_filename,
            )
            self.logger.exception(log_message)
            cleaner.LOGGER.exception(log_message)
            files = []
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        self.logger.info("%s, files: %s" % (self.name, files))

        # download the PDF files so their pages can be counted
        download_pdf_files_from_bucket(
            storage,
            files,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # validate the file contents
        try:
            self.statuses["valid"] = cleaner.check_files(
                files, asset_file_name_map, input_filename
            )
        except Exception:
            log_message = (
                "%s, unhandled exception in cleaner.check_files for file %s"
                % (self.name, input_filename)
            )
            self.logger.exception(log_message)
            self.log_statuses(input_filename)
        finally:
            # remove the log handlers
            for log_handler in cleaner_log_handers:
                cleaner.log_remove_handler(log_handler)

        # Send an email if the log has warnings
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        if "ERROR" in log_contents or "WARNING" in log_contents:
            # Send error email
            error_messages = (
                "Warnings found in the log file for zip file %s\n\n" % input_filename
            )
            error_messages += log_contents
            self.statuses["email"] = self.email_error_report(
                input_filename, error_messages
            )

        # add the log_contents to the session variable
        cleaner_log = session.get_value("cleaner_log")
        if cleaner_log is None:
            cleaner_log = log_contents
        else:
            print("hello!!")
            cleaner_log += log_contents
        session.store_value("cleaner_log", cleaner_log)

        self.log_statuses(input_filename)

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
    return "Error validating accepted submission file: {filename}".format(
        filename=filename
    )


def download_pdf_files_from_bucket(storage, files, asset_file_name_map, to_dir, logger):
    "download PDF files from the S3 bucket expanded folder to the local disk"
    pdf_files = cleaner.files_by_extension(files, "pdf")
    cleaner.download_asset_files_from_bucket(
        storage, pdf_files, asset_file_name_map, to_dir, logger
    )
