import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner, email_provider, utils
from activity.objects import AcceptedBaseActivity


REPAIR_XML = False


class activity_ValidateAcceptedSubmission(AcceptedBaseActivity):
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

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # check PRC status and store in the session
        try:
            prc_status = cleaner.is_prc(xml_file_path, input_filename)
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.is_prc"
                " parsing XML file %s for file %s"
            ) % (
                self.name,
                article_processing.file_name_from_name(xml_file_path),
                input_filename,
            )
            self.logger.exception(log_message)
            cleaner.LOGGER.exception(log_message)
            prc_status = None

        session.store_value("prc_status", prc_status)

        # get the preprint URL from the XML if present
        try:
            preprint_url = cleaner.preprint_url(xml_file_path)
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.preprint_url"
                " parsing XML file %s for file %s"
            ) % (
                self.name,
                article_processing.file_name_from_name(xml_file_path),
                input_filename,
            )
            self.logger.exception(log_message)
            cleaner.LOGGER.exception(log_message)
            preprint_url = None

        session.store_value("preprint_url", preprint_url)

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

        self.logger.info("%s, files: %s" % (self.name, files))

        # reset the parsing library flag
        cleaner.parse.REPAIR_XML = original_repair_xml

        # check whether PRC preprint data is present
        if prc_status:

            error_email_body = ""

            if not preprint_url:
                log_message = "Preprint URL was not found in the article XML"
                self.logger.info("%s, %s" % (self.name, log_message))

            # check docmap URL exists, if fails then fail the workflow
            docmap_url = cleaner.docmap_url(
                self.settings, session.get_value("article_id")
            )
            if not cleaner.url_exists(docmap_url, self.logger):
                log_message = (
                    "Request for a docmap was not successful for URL %s" % docmap_url
                )
                self.logger.info("%s, %s" % (self.name, log_message))
                error_email_body += "%s\n" % log_message

            if error_email_body:
                body_content = error_email_body_content(
                    error_email_body,
                    input_filename,
                    self.name,
                )
                self.statuses["email"] = self.send_error_email(
                    input_filename, body_content
                )
                self.log_statuses(input_filename)
                return self.ACTIVITY_PERMANENT_FAILURE

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
            self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def send_error_email(self, output_file, body_content):
        "email the message to the recipients"
        success = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = error_email_subject(output_file, self.settings)
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
            email_success = email_provider.smtp_send(
                connection, sender_email, recipient, email_message, self.logger
            )
            if not email_success:
                # for now any failure in sending a mail return False
                success = False
        return success


def download_pdf_files_from_bucket(storage, files, asset_file_name_map, to_dir, logger):
    "download PDF files from the S3 bucket expanded folder to the local disk"
    pdf_files = cleaner.files_by_extension(files, "pdf")
    cleaner.download_asset_files_from_bucket(
        storage, pdf_files, asset_file_name_map, to_dir, logger
    )


def error_email_subject(output_file, settings=None):
    "the email subject"
    subject_prefix = ""
    if utils.settings_environment(settings) == "continuumtest":
        subject_prefix = "TEST "
    return "%sError validating accepted submission file: %s" % (
        subject_prefix,
        output_file,
    )


def error_email_body_content(
    error_email_body,
    input_filename,
    activity_name,
):
    "body content of the error email for validating accepted submission"
    header = (
        (
            "Validation messages were generated in the %s "
            "workflow activity when processing input file %s\n\n"
        )
    ) % (activity_name, input_filename)
    body_content = header + error_email_body
    return body_content
