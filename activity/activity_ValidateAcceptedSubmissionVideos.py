import os
import json
import shutil
import time
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider import cleaner, email_provider, glencoe_check, utils
from activity.objects import AcceptedBaseActivity


REPAIR_XML = False


class activity_ValidateAcceptedSubmissionVideos(AcceptedBaseActivity):
    "ValidateAcceptedSubmissionVideos activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidateAcceptedSubmissionVideos, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ValidateAcceptedSubmissionVideos"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Check accepted submission videos for whether they should be processed "
            + "and deposited to a video service as part of the ingestion workflow."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"valid": None, "deposit_videos": None, "email_status": None}

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

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # reset the REPAIR_XML constant
        original_repair_xml = cleaner.parse.REPAIR_XML
        cleaner.parse.REPAIR_XML = REPAIR_XML

        # get list of video files from the article XML
        video_files = []
        try:
            video_files = cleaner.video_file_list(xml_file_path)
            self.logger.info(
                "%s, %s video_files: %s" % (self.name, input_filename, video_files)
            )
        except ParseError:
            log_message = "%s, XML ParseError exception parsing file %s for file %s" % (
                self.name,
                xml_file_path,
                input_filename,
            )
            self.logger.exception(log_message)
            self.log_statuses(input_filename)
        finally:
            # reset the parsing library flag
            cleaner.parse.REPAIR_XML = original_repair_xml

        ###### start validation checks
        if video_files:
            error_email_body = ""
            # generate video data from video_files
            generated_video_data = []
            try:
                generated_video_data = cleaner.video_data_from_files(
                    video_files, article_id
                )
            except Exception:
                log_message = (
                    "%s, exception invoking video_data_from_files() for file %s"
                    % (
                        self.name,
                        input_filename,
                    )
                )
                self.logger.exception(log_message)
                error_email_body += log_message
            # validate the video data
            if generated_video_data:
                validation_messages = validate_video_data(
                    generated_video_data, input_filename, self.name, self.logger
                )
                error_email_body += validation_messages
            if error_email_body:
                self.statuses["valid"] = False

            # set validation status if not already set
            if self.statuses.get("valid") is None:
                self.statuses["valid"] = True

        if self.statuses.get("valid") is False:
            # videos failed validation
            # send an email
            body_content = error_email_body_content(
                error_email_body,
                input_filename,
                self.name,
                video_files,
                generated_video_data,
            )
            self.statuses["email_status"] = self.send_error_email(
                input_filename, body_content
            )
            self.log_statuses(input_filename)
            return self.ACTIVITY_PERMANENT_FAILURE

        ###### end of validation checks

        # check for existing video metadata if there are videos
        if self.statuses.get("valid"):
            no_video_metadata = None
            try:
                gc_data = glencoe_check.metadata(
                    glencoe_check.check_msid(article_id), self.settings
                )
                self.logger.info(
                    "%s, %s gc_data: %s"
                    % (self.name, article_id, json.dumps(gc_data, indent=4))
                )
                no_video_metadata = False
            except AssertionError as exception:
                if str(exception).startswith("article has no videos"):
                    self.logger.info(
                        "%s, %s has no video metadata" % (self.name, article_id)
                    )
                    no_video_metadata = True

            # deposit the videos later only if there is no metadata already available
            self.statuses["deposit_videos"] = no_video_metadata

        # set session value
        if self.statuses.get("deposit_videos") is not None:
            session.store_value("deposit_videos", self.statuses["deposit_videos"])

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


def error_email_subject(output_file, settings=None):
    "the email subject"
    subject_prefix = ""
    if utils.settings_environment(settings) == "continuumtest":
        subject_prefix = "TEST "
    return "%sError validating videos in accepted submission file: %s" % (
        subject_prefix,
        output_file,
    )


def error_email_body_content(
    error_email_body, input_filename, activity_name, video_files, generated_video_data
):
    "body content of the error email for validating accepted submission video data"
    header = (
        (
            "Validation messages were generated in the %s "
            "workflow activity when processing input file %s\n\n"
            "Log messages:\n\n"
        )
    ) % (activity_name, input_filename)
    body_content = header + error_email_body
    body_content += "\n\nVideo file data from the XML:\n\n%s" % json.dumps(
        video_files, indent=4
    )
    body_content += "\n\nVideo data generated:\n\n%s" % json.dumps(
        generated_video_data, indent=4
    )
    return body_content


def validate_video_data(generated_video_data, input_filename, activity_name, logger):
    "run validation checks on the generated video data"
    validation_messages = ""

    # check if any video data has incomplete data
    for video_data in generated_video_data:
        if not video_data.get("video_id"):
            log_message = (
                '%s, %s video file name "%s" generated a video_id value of %s'
                % (
                    activity_name,
                    input_filename,
                    video_data.get("upload_file_nm"),
                    video_data.get("video_id"),
                )
            )
            logger.info(log_message)
            validation_messages += log_message
        if not video_data.get("video_filename"):
            log_message = (
                '%s, %s video file name "%s" generated a video_filename value of %s'
                % (
                    activity_name,
                    input_filename,
                    video_data.get("upload_file_nm"),
                    video_data.get("video_filename"),
                )
            )
            logger.info(log_message)
            validation_messages += log_message
    # check if there are any duplicate names generated
    video_id_list = [video_data.get("video_id") for video_data in generated_video_data]
    video_filename_list = [
        video_data.get("video_filename") for video_data in generated_video_data
    ]
    unique_video_ids = list(
        {str(video_data.get("video_id")) for video_data in generated_video_data}
    )
    unique_video_filenames = list(
        {str(video_data.get("video_filename")) for video_data in generated_video_data}
    )
    if len(video_id_list) != len(unique_video_ids) or len(video_filename_list) != len(
        unique_video_filenames
    ):
        log_message = "%s, %s duplicate video_id or video_filename generated" % (
            activity_name,
            input_filename,
        )
        logger.info(log_message)
        validation_messages += log_message
    return validation_messages
