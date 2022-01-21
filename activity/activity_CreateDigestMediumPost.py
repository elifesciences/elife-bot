import os
import json
import time
from digestparser import medium_post
from provider.article_processing import download_jats
from provider import digest_provider, email_provider, utils
from activity.objects import Activity


class activity_CreateDigestMediumPost(Activity):
    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_CreateDigestMediumPost, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "CreateDigestMediumPost"
        self.pretty_name = "Create Digest Medium Post"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Create a post on Medium for a digest."

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {}

        # Digest JSON content
        self.medium_content = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # get data
        (
            success,
            run,
            article_id,
            version,
            status,
            expanded_folder,
            run_type,
        ) = self.parse_data(data)
        if success is not True:
            self.logger.error("Failed to parse data in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE
        # emit start message
        emit_success = self.emit_start_message(article_id, version, run)
        if emit_success is not True:
            self.logger.error("Failed to emit a start message in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # check if required credentials are set first before continuing
        required_credentials = [
            "medium_application_client_id",
            "medium_application_client_secret",
            "medium_access_token",
        ]
        missing_credentials = [
            cred_name
            for cred_name in required_credentials
            if not self.digest_config.get(cred_name)
        ]
        if missing_credentials:
            self.logger.info(
                "Missing credentials, %s, in create digest Medium post, article %s"
                % (missing_credentials, article_id)
            )
            self.emit_end_message(article_id, version, run)
            return self.ACTIVITY_SUCCESS

        # Wrap in an exception during testing phase
        try:
            # check if there is a digest docx in the bucket for this article
            docx_file_exists = digest_provider.docx_exists_in_s3(
                self.settings, article_id, self.settings.bot_bucket, self.logger
            )
            if docx_file_exists is not True:
                self.logger.info(
                    "Digest docx file does not exist in S3 for article %s" % article_id
                )
                self.emit_end_message(article_id, version, run)
                return self.ACTIVITY_SUCCESS

            # Approve for creating a Medium post
            self.statuses["approve"] = self.approve(
                article_id, status, version, run_type
            )
            if self.statuses.get("approve") is not True:
                self.logger.info(
                    "Digest for article %s not approved for creating a Medium post"
                    % article_id
                )
                self.emit_end_message(article_id, version, run)
                return self.ACTIVITY_SUCCESS

            # create the digest content from the docx and JATS file
            # download jats file
            docx_file = digest_provider.download_docx_from_s3(
                self.settings,
                article_id,
                self.settings.bot_bucket,
                self.directories.get("INPUT_DIR"),
                self.logger,
            )

            jats_file = download_jats(
                self.settings,
                expanded_folder,
                self.directories.get("TEMP_DIR"),
                self.logger,
            )

            # find the image file name
            image_file_name = digest_provider.image_file_name_from_s3(
                self.settings, article_id, self.settings.bot_bucket
            )

            # generate the digest content
            self.medium_content = self.build_medium_content(
                docx_file, jats_file, image_file_name
            )
            if self.medium_content:
                self.statuses["generate"] = True

            # POST to the Medium API endpoint
            if self.medium_content:
                self.statuses["post"] = post_medium_content(
                    self.medium_content, self.digest_config, self.logger
                )

            if self.statuses.get("post"):
                # Email
                self.statuses["email"] = self.email_notification(article_id)

        except Exception as exception:
            self.logger.exception(
                (
                    "Exception raised in do_activity of %s, article_id %s, version %s. Details: %s"
                    % (self.name, article_id, version, str(exception))
                )
            )

        self.emit_end_message(article_id, version, run)

        return self.ACTIVITY_SUCCESS

    def parse_data(self, data):
        "extract individual values from the activity data"
        run = None
        article_id = None
        version = None
        status = None
        expanded_folder = None
        run_type = None
        success = None
        try:
            run = data.get("run")
            article_id = data.get("article_id")
            version = data.get("version")
            status = data.get("status")
            expanded_folder = data.get("expanded_folder")
            run_type = data.get("run_type")
            success = True
        except (TypeError, KeyError) as exception:
            self.logger.exception(
                "Exception parsing the input data in %s."
                + " Details: %s" % self.pretty_name,
                str(exception),
            )
        return success, run, article_id, version, status, expanded_folder, run_type

    def build_medium_content(self, docx_file, jats_file=None, image_file_name=None):
        """generate the medium content from the docx file and other data"""
        json_content = None
        try:
            json_content = medium_post.build_medium_content(
                docx_file,
                self.directories.get("TEMP_DIR"),
                self.digest_config,
                jats_file,
                image_file_name,
            )
        except Exception as exception:
            self.logger.exception(
                "Exception generating digest json for docx_file %s. Details: %s"
                % (str(docx_file), str(exception))
            )
        return json_content

    def emit_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                status,
                message,
            )
            return True
        except Exception as exception:
            self.logger.exception(
                "Exception emitting %s message. Details: %s"
                % (str(status), str(exception))
            )

    def emit_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_message(
            article_id,
            version,
            run,
            "start",
            "Starting %s for %s" % (self.pretty_name, article_id),
        )

    def emit_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_message(
            article_id,
            version,
            run,
            "end",
            "Finished %s for %s. Statuses: %s"
            % (self.pretty_name, article_id, self.statuses),
        )

    def emit_error_message(self, article_id, version, run, message):
        "emit an error message to the queue"
        return self.emit_message(article_id, version, run, "error", message)

    def approve(self, article_id, status, version, run_type):
        """should it create a Medium post based on some basic attributes"""
        approve_status = True

        # check by status
        return_status = digest_provider.approve_by_status(
            self.logger, article_id, status
        )
        if return_status is False:
            approve_status = False

        # check silent correction
        if run_type == "silent-correction":
            approve_status = False
        else:
            first_vor_status = digest_provider.approve_by_first_vor(
                self.settings, self.logger, article_id, version, status
            )
            if first_vor_status is False:
                approve_status = False

        return approve_status

    def email_notification(self, article_id):
        "email the success notification to the recipients"
        success = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string)
        subject = success_email_subject(article_id)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_medium_recipient_email
        )

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger
        )
        self.logger.info("Formatted %d messages in %s" % (len(messages), self.name))

        details = email_provider.smtp_send_messages(
            self.settings, messages, self.logger
        )
        self.logger.info("Email sending details: %s" % str(details))

        return success


def post_medium_content(medium_content, digest_config, logger):
    if medium_content:
        try:
            post_return = medium_post.post_content(medium_content, digest_config)
            logger.info("Medium post return: %s" % post_return)
            return True
        except Exception as exception:
            logger.exception(
                "Exception raised posting to Medium. Details: %s" % str(exception)
            )
        return False


def success_email_subject(article_id):
    "the email subject"
    return u"Medium post created for Digest: {msid:0>5}".format(msid=str(article_id))
