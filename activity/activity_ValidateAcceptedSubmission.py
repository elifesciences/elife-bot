import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, email_provider
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

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")

        # get list of bucket objects from expanded folder
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        self.logger.info(
            "%s, asset_file_name_map: %s" % (self.name, asset_file_name_map)
        )

        # find S3 object for article XML and download it
        xml_file_path = download_xml_file_from_bucket(
            storage,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # get list of files from the article XML
        files = cleaner.file_list(xml_file_path)
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
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.check_files for file %s"
                % (self.name, input_filename)
            )
            self.logger.exception(log_message)
            # Send error email
            self.statuses["email"] = self.email_error_report(
                input_filename, log_message
            )
            self.log_statuses(input_filename)
        except Exception:
            log_message = (
                "%s, unhandled exception in cleaner.check_files for file %s"
                % (self.name, input_filename)
            )
            self.logger.exception(log_message)
            # Send error email
            self.statuses["email"] = self.email_error_report(
                input_filename, log_message
            )
            self.log_statuses(input_filename)
            return self.ACTIVITY_PERMANENT_FAILURE
        finally:
            # remove the log handlers
            for log_handler in cleaner_log_handers:
                cleaner.log_remove_handler(log_handler)
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        # Send an email if the log has warnings
        log_contents = ""
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()
        if "WARNING" in log_contents:
            # Send error email
            error_messages = (
                "Warnings found in the log file for zip file %s\n\n" % input_filename
            )
            error_messages += log_contents
            self.statuses["email"] = self.email_error_report(
                input_filename, error_messages
            )

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


def download_xml_file_from_bucket(storage, asset_file_name_map, to_dir, logger):
    "download article XML file from the S3 bucket expanded folder to the local disk"
    xml_file_asset = cleaner.article_xml_asset(asset_file_name_map)
    asset_key, asset_resource = xml_file_asset
    xml_file_path = os.path.join(to_dir, asset_key)
    logger.info("Downloading XML file from %s to %s" % (asset_resource, xml_file_path))
    # create folders if they do not exist
    os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)
    with open(xml_file_path, "wb") as open_file:
        storage.get_resource_to_file(asset_resource, open_file)
        # rewrite asset_file_name_map to the local value
        asset_file_name_map[asset_key] = xml_file_path
    return xml_file_path


def download_pdf_files_from_bucket(storage, files, asset_file_name_map, to_dir, logger):
    "download PDF files from the S3 bucket expanded folder to the local disk"
    pdf_files = cleaner.files_by_extension(files, "pdf")

    # map values without folder names in order to later match XML files names to zip file path
    asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}

    for pdf_file in pdf_files:
        file_name = pdf_file.get("upload_file_nm")
        asset_key = asset_key_map[file_name]
        asset_resource = asset_file_name_map.get(asset_key)
        file_path = os.path.join(to_dir, file_name)
        logger.info("Downloading PDF file from %s to %s" % (asset_resource, file_path))
        # create folders if they do not exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as open_file:
            storage.get_resource_to_file(asset_resource, open_file)
        # rewrite asset_file_name_map to the local value
        asset_file_name_map[asset_key] = file_path
