import os
import json
import time
from collections import OrderedDict
import requests
import digestparser.utils as digest_utils
from elifetools.utils import doi_uri_to_doi
from S3utility.s3_notification_info import parse_activity_data
from provider import digest_provider, email_provider
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
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

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
            self.logger.info('PostDigestJATS silent deposit of real_filename: %s', real_filename)
            return self.ACTIVITY_SUCCESS

        # Download from S3
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)

        # Parse input and build digest
        self.statuses["build"], self.digest = digest_provider.build_digest(
            self.input_file, self.temp_dir, self.logger, self.digest_config)

        # Generate jats
        self.jats_content = digest_provider.digest_jats(self.digest)

        if self.jats_content:
            self.statuses["jats"] = True

        # POST to API endpoint
        try:
            self.statuses["post"] = self.post_jats(self.digest, self.jats_content)
            # send email
            if self.statuses.get("post"):
                self.statuses["email"] = self.send_email(self.digest, self.jats_content)
        except Exception as exception:
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))

        self.logger.info(
            "%s for real_filename %s statuses: %s" % (self.name, str(real_filename), self.statuses))

        if self.statuses.get("jats"):
            return self.ACTIVITY_SUCCESS

        return self.ACTIVITY_PERMANENT_FAILURE

    def post_jats(self, digest, jats_content):
        """prepare and POST jats to API endpoint"""
        url = self.settings.typesetter_digest_endpoint
        payload = post_payload(digest, jats_content, self.settings.typesetter_digest_api_key)
        if payload:
            return post_jats_to_endpoint(url, payload, self.logger)
        return None

    def send_email(self, digest_content, jats_content):
        """send an email after digest JATS is posted to endpoint"""
        success = True

        current_time = time.gmtime()
        body = success_email_body(current_time, digest_content, jats_content)
        subject = success_email_subject(digest_content)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_recipient_email)

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_success = email_provider.smtp_send(connection, sender_email, recipient,
                                                     email_message, self.logger)
            if not email_success:
                # for now any failure in sending a mail return False
                success = False
        return success

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass


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
    resp = get_as_params(url, payload)
    # Check for good HTTP status code
    if resp.status_code != 200:
        logger.error(
            ("Error posting digest JATS to endpoint %s: \npayload: %s \nstatus_code: %s" +
             " \nresponse: %s") %
            (url, payload, resp.status_code, resp.content))
        return False
    logger.info(
        ("Success posting digest JATS to endpoint %s: \npayload: %s \nstatus_code: %s" +
         " \nresponse: %s") %
        (url, payload, resp.status_code, resp.content))
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
    """the email subject"""
    if not digest_content:
        return u''
    try:
        doi = getattr(digest_content, 'doi')
        msid = doi.split(".")[-1]
    except AttributeError:
        msid = None
    return u'Digest JATS posted for article {msid:0>5}, author {author}'.format(
        msid=str(msid), author=digest_utils.unicode_decode(digest_content.author))


def success_email_body(current_time, digest_content, jats_content):
    """
    Format the body of the email
    """
    body = "JATS content for article %s:\n\n%s\n\n" % (
        str(digest_content.doi), str(jats_content))
    date_format = '%Y-%m-%dT%H:%M:%S.000Z'
    datetime_string = time.strftime(date_format, current_time)
    body += "As at " + datetime_string + "\n"
    body += "\n"
    body += "\n\nSincerely\n\neLife bot"
    return body
