import os
import json
import time
from requests.exceptions import HTTPError
from elifetools.utils import doi_uri_to_doi
from S3utility.s3_notification_info import parse_activity_data
from provider import (
    digest_provider,
    download_helper,
    email_provider,
    requests_provider,
    utils,
)
from activity.objects import Activity


class activity_PostDigestJATS(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PostDigestJATS, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "PostDigestJATS"
        self.pretty_name = "POST Digest JATS content to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "POST Digest JATS content to API endpoint,"
            + " to be run when a digest package is first ingested"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"build": None, "jats": None, "post": None}

        # Track some values
        self.input_file = None
        self.digest = None
        self.jats_content = None
        self.post_error_message = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # first check if there is an endpoint in the settings specified
        if not hasattr(self.settings, "typesetter_digest_endpoint"):
            self.logger.info(
                "No typesetter endpoint in settings, skipping %s.", self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.typesetter_digest_endpoint:
            self.logger.info(
                "Typesetter endpoint in settings is blank, skipping %s.", self.name
            )
            return self.ACTIVITY_SUCCESS

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # check if it is a silent run
        if digest_provider.silent_digest(real_filename):
            self.logger.info(
                "PostDigestJATS is not posting JATS because it is a silent workflow, "
                + "real_filename: %s",
                real_filename,
            )
            return self.ACTIVITY_SUCCESS

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
        if not self.statuses.get("build"):
            error_message = "Failed to build digest from file %s" % self.input_file
            self.logger.info(error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, error_message
            )
            return self.ACTIVITY_SUCCESS

        # Generate jats
        self.jats_content = digest_provider.digest_jats(self.digest)

        if self.jats_content:
            self.statuses["jats"] = True
        else:
            error_message = (
                "Failed to generate digest JATS from file %s" % self.input_file
            )
            self.logger.info(error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, error_message
            )
            return self.ACTIVITY_SUCCESS

        # POST to API endpoint
        try:
            self.post_jats(self.digest, self.jats_content)
            self.statuses["post"] = True
        except HTTPError as exception:
            # post was not a success, send error email
            self.statuses["post"] = False
            self.post_error_message = "POST was not successful, details: %s" % str(
                exception
            )
            self.logger.exception(self.post_error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, self.post_error_message
            )
        except Exception as exception:
            # exception, send error email
            self.statuses["post"] = False
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, str(exception)
            )
            self.logger.exception(
                "Exception raised in do_activity. Details: %s" % str(exception)
            )

        # send success email
        if self.statuses.get("post"):
            self.statuses["email"] = self.send_email(self.digest, self.jats_content)

        self.logger.info(
            "%s for real_filename %s statuses: %s"
            % (self.name, str(real_filename), self.statuses)
        )

        return self.ACTIVITY_SUCCESS

    def post_jats(self, digest, jats_content):
        """prepare and POST jats to API endpoint"""
        url = self.settings.typesetter_digest_endpoint
        params = requests_provider.jats_post_params(
            self.settings.typesetter_digest_api_key
        )
        doi = utils.msid_from_doi(doi_uri_to_doi(digest.doi))
        payload = requests_provider.jats_post_payload(
            "digest",
            doi,
            jats_content,
            self.settings.typesetter_digest_api_key,
            self.settings.typesetter_digest_account_key,
        )
        content_type = "application/x-www-form-urlencoded"
        if payload:
            requests_provider.post_to_endpoint(
                url,
                payload,
                self.logger,
                "digest JATS",
                params=params,
                content_type=content_type,
            )

    def send_email(self, digest_content, jats_content):
        """send an email after digest JATS is posted to endpoint"""
        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body_content = requests_provider.success_email_body_content(
            digest_content.doi, jats_content
        )
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = requests_provider.success_email_subject_msid_author(
            "Digest ",
            digest_provider.get_digest_msid(digest_content),
            digest_content.author,
        )
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_jats_recipient_email
        )

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger
        )
        self.logger.info(
            "Formatted %d email messages in %s" % (len(messages), self.name)
        )

        details = email_provider.smtp_send_messages(
            self.settings, messages, self.logger
        )
        self.logger.info("Email sending details: %s" % str(details))

        return True

    def email_error_report(self, digest_content, jats_content, error_messages):
        """send an email on error"""
        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        doi = None
        if digest_content:
            doi = digest_content.doi
        body_content = requests_provider.error_email_body_content(
            doi, jats_content, error_messages
        )
        body = email_provider.simple_email_body(datetime_string, body_content)
        author = None
        if digest_content:
            author = digest_content.author
        subject = requests_provider.error_email_subject_msid_author(
            "digest", digest_provider.get_digest_msid(digest_content), author
        )
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_jats_error_recipient_email
        )

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger
        )
        self.logger.info(
            "Formatted %d error email messages in %s" % (len(messages), self.name)
        )

        details = email_provider.smtp_send_messages(
            self.settings, messages, self.logger
        )
        self.logger.info("Email sending details: %s" % str(details))

        return True
