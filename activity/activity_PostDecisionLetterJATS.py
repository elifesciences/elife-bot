import os
import json
import time
from requests.exceptions import HTTPError
from provider import (
    download_helper, email_provider, letterparser_provider, requests_provider, utils)
from provider.execution_context import get_session
from activity.objects import Activity


class activity_PostDecisionLetterJATS(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PostDecisionLetterJATS, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PostDecisionLetterJATS"
        self.pretty_name = "POST decision letter JATS content to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = self.pretty_name

        # Track some values
        self.xml_file = None
        self.doi = None
        self.post_error_message = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        # Track the success of some steps
        self.statuses = {
            "post": None,
            "email": None,
            "error_email": None
        }

        # Load the config
        self.letterparser_config = letterparser_provider.letterparser_config(self.settings)

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # session
        run = data['run']
        session = get_session(self.settings, data, run)

        bucket_folder_name = session.get_value('bucket_folder_name')
        xml_file_name = session.get_value('xml_file_name')
        output_bucket_name = self.settings.decision_letter_output_bucket

        # check for session data
        if not bucket_folder_name or not xml_file_name:
            self.logger.error('Missing session data in %s.' % self.name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # check if there is an endpoint in the settings specified
        if not hasattr(self.settings, "typesetter_decision_letter_endpoint"):
            self.logger.error("No typesetter endpoint in settings, skipping %s." % self.name)
            return self.ACTIVITY_PERMANENT_FAILURE
        if not self.settings.typesetter_decision_letter_endpoint:
            self.logger.error("Typesetter endpoint in settings is blank, skipping %s." % self.name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # download XML from S3 bucket
        self.xml_file = download_helper.download_file_from_s3(
            self.settings, xml_file_name, output_bucket_name, bucket_folder_name,
            self.directories.get("INPUT_DIR"))

        # get doi from the xml string
        xml_string = None
        try:
            with open(self.xml_file, 'r') as open_file:
                xml_string = open_file.read()
            self.doi = letterparser_provider.article_doi_from_xml(xml_string)
        except:
            self.logger.exception(
                "Failed to get doi from xml_string in %s for xml_file %s" %
                (self.name, self.xml_file))
            return self.ACTIVITY_PERMANENT_FAILURE

        # POST to API endpoint
        try:
            self.post_jats(self.doi, xml_string)
            self.statuses["post"] = True
        except HTTPError as exception:
            # post was not a success, send error email
            self.statuses["post"] = False
            self.post_error_message = "POST was not successful, details: %s" % str(exception)
            self.logger.exception(self.post_error_message)
            self.statuses["error_email"] = self.email_error_report(
                self.doi, xml_string, self.post_error_message)
            return self.ACTIVITY_PERMANENT_FAILURE
        except Exception as exception:
            # exception, send error email
            self.statuses["post"] = False
            self.statuses["error_email"] = self.email_error_report(
                self.doi, xml_string, str(exception))
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        # send success email
        if self.statuses.get("post"):
            self.statuses["email"] = self.send_email(self.doi, xml_string)

        self.logger.info(
            "%s for real_filename %s statuses: %s" % (self.name, str(self.xml_file), self.statuses))

        return self.ACTIVITY_SUCCESS

    def post_jats(self, doi, jats_content):
        """prepare and POST jats to API endpoint"""
        url = self.settings.typesetter_decision_letter_endpoint
        payload = requests_provider.jats_post_payload(
            'decision', doi, jats_content, self.settings.typesetter_decision_letter_api_key)
        if payload:
            requests_provider.post_to_endpoint(
                url, payload, self.logger, 'decision letter JATS')

    def send_email(self, doi, jats_content):
        """send an email after JATS is posted to endpoint"""
        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body_content = success_email_body_content(doi, jats_content)
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = success_email_subject(doi)
        sender_email = self.settings.decision_letter_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.decision_letter_jats_recipient_email)

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger)
        self.logger.info('Formatted %d email messages in %s' % (len(messages), self.name))

        details = email_provider.smtp_send_messages(self.settings, messages, self.logger)
        self.logger.info('Email sending details: %s' % str(details))

        return True

    def email_error_report(self, doi, jats_content, error_messages):
        """send an email on error"""
        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body_content = error_email_body_content(doi, jats_content, error_messages)
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = error_email_subject(doi)
        sender_email = self.settings.decision_letter_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.decision_letter_jats_error_recipient_email)

        messages = email_provider.simple_messages(
            sender_email, recipient_email_list, subject, body, logger=self.logger)
        self.logger.info('Formatted %d error email messages in %s' % (len(messages), self.name))

        details = email_provider.smtp_send_messages(self.settings, messages, self.logger)
        self.logger.info('Email sending details: %s' % str(details))

        return True


def success_email_subject(doi):
    """email subject for a success email"""
    return u'Decision letter JATS posted for article {doi}'.format(
        doi=str(doi))


def success_email_body_content(doi, jats_content):
    """
    Format the body content of the email
    """
    return "JATS content for article %s:\n\n%s\n\n" % (doi, jats_content)


def error_email_subject(doi):
    """email subject for an error email"""
    return u'Error in decision letter JATS post for article {doi}'.format(
        doi=str(doi))


def error_email_body_content(doi, jats_content, error_messages):
    """body content of an error email"""
    content = ""
    if error_messages:
        content += str(error_messages)
        content += "\n\nMore details about the error may be found in the worker.log file\n\n"
    if doi:
        content += "Article DOI: %s\n\n" % doi
    content += "JATS content: %s\n\n" % jats_content
    return content
