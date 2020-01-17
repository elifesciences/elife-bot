import os
import json
import time
from collections import OrderedDict
import requests
import digestparser.utils as digest_utils
from elifetools.utils import doi_uri_to_doi
from S3utility.s3_notification_info import parse_activity_data
from provider import digest_provider, download_helper, email_provider
from activity.objects import Activity


class activity_PostDigestJATS(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PostDigestJATS, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PostDigestJATS"
        self.pretty_name = "POST Digest JATS content to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("POST Digest JATS content to API endpoint," +
                            " to be run when a digest package is first ingested")

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        # Track the success of some steps
        self.statuses = {
            "build": None,
            "jats": None,
            "post": None
        }

        # Track some values
        self.input_file = None
        self.digest = None
        self.jats_content = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section,
            self.settings.digest_config_file)

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # first check if there is an endpoint in the settings specified
        if not hasattr(self.settings, "typesetter_digest_endpoint"):
            self.logger.info("No typesetter endpoint in settings, skipping %s.", self.name)
            return self.ACTIVITY_SUCCESS
        if not self.settings.typesetter_digest_endpoint:
            self.logger.info("Typesetter endpoint in settings is blank, skipping %s.", self.name)
            return self.ACTIVITY_SUCCESS

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # check if it is a silent run
        if digest_provider.silent_digest(real_filename):
            self.logger.info(
                'PostDigestJATS is not posting JATS because it is a silent workflow, ' +
                'real_filename: %s', real_filename)
            return self.ACTIVITY_SUCCESS

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder,
            self.directories.get("INPUT_DIR"))

        # Parse input and build digest
        self.statuses["build"], self.digest = digest_provider.build_digest(
            self.input_file, self.directories.get("TEMP_DIR"), self.logger, self.digest_config)
        if not self.statuses.get("build"):
            error_message = "Failed to build digest from file %s" % self.input_file
            self.logger.info(error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, error_message)
            return self.ACTIVITY_SUCCESS

        # Generate jats
        self.jats_content = digest_provider.digest_jats(self.digest)

        if self.jats_content:
            self.statuses["jats"] = True
        else:
            error_message = "Failed to generate digest JATS from file %s" % self.input_file
            self.logger.info(error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, error_message)
            return self.ACTIVITY_SUCCESS

        # POST to API endpoint
        try:
            post_jats_return_value = self.post_jats(self.digest, self.jats_content)
            if post_jats_return_value is True:
                self.statuses["post"] = True
                post_jats_error_message = ""
            else:
                self.statuses["post"] = False
                post_jats_error_message = str(post_jats_return_value)
            # send email
            if self.statuses.get("post"):
                self.statuses["email"] = self.send_email(self.digest, self.jats_content)
            else:
                # post was not a success, send error email
                error_message = "POST was not successful, details: %s" % post_jats_error_message
                self.statuses["error_email"] = self.email_error_report(
                    self.digest, self.jats_content, error_message)
        except Exception as exception:
            # exception, send error email
            self.statuses["error_email"] = self.email_error_report(
                self.digest, self.jats_content, str(exception))
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))

        self.logger.info(
            "%s for real_filename %s statuses: %s" % (self.name, str(real_filename), self.statuses))

        return self.ACTIVITY_SUCCESS

    def post_jats(self, digest, jats_content):
        """prepare and POST jats to API endpoint"""
        url = self.settings.typesetter_digest_endpoint
        payload = post_payload(digest, jats_content, self.settings.typesetter_digest_api_key)
        if payload:
            return post_jats_to_endpoint(url, payload, self.logger)
        return None

    def send_email(self, digest_content, jats_content):
        """send an email after digest JATS is posted to endpoint"""
        datetime_string = time.strftime('%Y-%m-%d %H:%M', time.gmtime())
        body_content = success_email_body_content(digest_content, jats_content)
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = success_email_subject(digest_content)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_jats_recipient_email)

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger)
        self.logger.info('Formatted %d email messages in %s' % (len(messages), self.name))

        details = email_provider.smtp_send_messages(self.settings, messages, self.logger)
        self.logger.info('Email sending details: %s' % str(details))

        return True

    def email_error_report(self, digest_content, jats_content, error_messages):
        """send an email on error"""
        datetime_string = time.strftime('%Y-%m-%d %H:%M', time.gmtime())
        body_content = error_email_body_content(digest_content, jats_content, error_messages)
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = error_email_subject(digest_content)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_jats_error_recipient_email)

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger)
        self.logger.info('Formatted %d error email messages in %s' % (len(messages), self.name))

        details = email_provider.smtp_send_messages(self.settings, messages, self.logger)
        self.logger.info('Email sending details: %s' % str(details))

        return True


def post_payload(digest, jats_content, api_key):
    """compile the POST data payload"""
    if not digest:
        return None
    account_key = 1
    content_type = "digest"
    payload = OrderedDict()
    payload["apiKey"] = api_key
    payload["accountKey"] = account_key
    payload["doi"] = doi_uri_to_doi(digest.doi)
    payload["type"] = content_type
    payload["content"] = jats_content
    return payload


def post_jats_to_endpoint(url, payload, logger):
    """issue the POST"""
    resp = post_as_data(url, payload)
    # Check for good HTTP status code
    if resp.status_code != 200:
        response_error_message = (
            "Error posting digest JATS to endpoint %s: status_code: %s\nresponse: %s" %
            (url, resp.status_code, resp.content))
        full_error_message = (
            "%s\npayload: %s" %
            (response_error_message, payload))
        logger.error(full_error_message)
        return response_error_message
    logger.info(
        ("Success posting digest JATS to endpoint %s: status_code: %s\nresponse: %s" +
         " \npayload: %s") %
        (url, resp.status_code, resp.content, payload))
    return True


def get_as_params(url, payload):
    """transmit the payload as a GET with URL parameters"""
    return requests.get(url, params=payload)


def post_as_params(url, payload):
    """post the payload as URL parameters"""
    return requests.post(url, params=payload)


def post_as_data(url, payload):
    """post the payload as form data"""
    return requests.post(url, data=payload)


def post_as_json(url, payload):
    """post the payload as JSON data"""
    return requests.post(url, json=payload)


def success_email_subject(digest_content):
    """email subject for a success email"""
    if not digest_content:
        return u''
    return u'Digest JATS posted for article {msid:0>5}, author {author}'.format(
        msid=str(digest_provider.get_digest_msid(digest_content)),
        author=digest_content.author)


def success_email_body_content(digest_content, jats_content):
    """
    Format the body content of the email
    """
    return "JATS content for article %s:\n\n%s\n\n" % (digest_content.doi, jats_content)


def error_email_subject(digest_content):
    """email subject for an error email"""
    if not digest_content:
        return u''
    return u'Error in digest JATS post for article {msid:0>5}, author {author}'.format(
        msid=str(digest_provider.get_digest_msid(digest_content)),
        author=digest_content.author)


def error_email_body_content(digest_content, jats_content, error_messages):
    """body content of an error email"""
    content = ""
    if error_messages:
        content += str(error_messages)
        content += "\n\nMore details about the error may be found in the worker.log file\n\n"
    if hasattr(digest_content, "doi"):
        content += "Article DOI: %s\n\n" % digest_content.doi
    content += "JATS content: %s\n\n" % jats_content
    return content
