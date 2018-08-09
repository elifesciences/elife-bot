import os
import json
import time
import boto.swf
from elifetools.utils import unicode_value
from digestparser import output
import digestparser.conf as digest_conf
import digestparser.utils as digest_utils
from S3utility.s3_notification_info import parse_activity_data
import provider.digest_provider as digest_provider
import provider.email_provider as email_provider
from .activity import Activity


class activity_EmailDigest(Activity):
    "EmailDigest activity"
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_EmailDigest, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "EmailDigest"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Download digest file input from the bucket, parse it, generate the " +
                            "output and send it in an email to recipients.")

        # Track some values
        self.input_file = None
        self.digest = None

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")
        self.output_dir = os.path.join(self.get_tmp_dir(), "output_dir")

        # Create output directories
        self.create_activity_directories()

        # Track the success of some steps
        self.activity_status = None
        self.build_status = None
        self.generate_status = None
        self.approve_status = None
        self.email_status = None

        # Load the config
        self.digest_config = self.elifedigest_config(self.settings.digest_config_section)

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = digest_provider.download_digest_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder, self.input_dir)

        # Parse input and build digest
        self.build_status, self.digest = digest_provider.build_digest(
            self.input_file, self.temp_dir, self.logger)

        # Generate output
        self.generate_status, output_file = self.generate_output(self.digest)

        if self.generate_status is True:
            self.activity_status = True

        # Approve files for emailing
        self.approve_status, error_message = approve_sending(self.digest)

        if self.approve_status is True and self.generate_status is True:
            # Email file
            self.email_status = self.email_digest(self.digest, output_file)
        else:
            # Send error email
            self.email_status = self.email_error_report(real_filename, error_message)

        # return a value based on the activity_status
        if self.activity_status is True:
            return True

        return self.ACTIVITY_PERMANENT_FAILURE

    def elifedigest_config(self, config_section):
        "parse the config values from the digest config"
        return digest_conf.parse_raw_config(digest_conf.raw_config(
            config_section,
            self.settings.digest_config_file))

    def generate_output(self, digest_content):
        "From the parsed digest content generate the output"
        if not digest_content:
            return False, None
        file_name = output_file_name(digest_content, self.digest_config)
        self.logger.info('EmailDigest output file_name: %s', file_name)
        full_file_name = output_file = os.path.join(self.output_dir, unicode_value(file_name))
        self.logger.info('EmailDigest output full_file_name: %s', full_file_name)
        try:
            output_file = output.digest_docx(digest_content, full_file_name, '')
        except UnicodeEncodeError as exception:
            self.logger.exception("EmailDigest generate_output exception. Message: %s",
                                  exception.message)
            return False, None
        return True, output_file

    def email_digest(self, digest_content, output_file):
        "email the digest as an attachment to the recipients"
        success = True

        current_time = time.gmtime()
        body = success_email_body(current_time)
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
            email_provider.add_attachment(email_message, output_file)
            # send the email
            email_success = email_provider.smtp_send(connection, sender_email, recipient,
                                                     email_message, self.logger)
            if not email_success:
                # for now any failure in sending a mail return False
                success = False
        return success

    def email_error_report(self, filename, error_message=None):
        "send an email on error"
        current_time = time.gmtime()
        body = error_email_body(current_time, error_message)
        subject = error_email_subject(filename)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_error_recipient_email)

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_provider.smtp_send(connection, sender_email, recipient,
                                     email_message, self.logger)
        return True

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir, self.output_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass


def approve_sending(digest_content):
    "validate the data for whether it is suitable to email"
    approve_status = True
    error_message = ''

    if not digest_content:
        approve_status = False
        error_message += '\nDigest was empty'
    if digest_content and not digest_content.author:
        approve_status = False
        error_message += '\nDigest author is missing'
    if digest_content and not digest_content.doi:
        approve_status = False
        error_message += '\nDigest DOI is missing'

    return approve_status, error_message


def output_file_name(digest_content, digest_config=None):

    "from the digest content return the file name for the DOCX output"
    if not digest_content:
        return
    # use the digestparser library to generate the output docx file name
    return output.docx_file_name(digest_content, digest_config)


def success_email_subject(digest_content):
    "the email subject"
    if not digest_content:
        return
    try:
        doi = getattr(digest_content, 'doi')
        msid = doi.split(".")[-1]
    except AttributeError:
        msid = None
    return u'Digest: {author}_{msid:0>5}'.format(
        author=digest_utils.unicode_decode(digest_content.author), msid=str(msid))


def success_email_body(current_time):
    """
    Format the body of the email
    """
    body = ""
    date_format = '%Y-%m-%dT%H:%M:%S.000Z'
    datetime_string = time.strftime(date_format, current_time)
    body += "As at " + datetime_string + "\n"
    body += "\n"
    body += "\n\nSincerely\n\neLife bot"
    return body


def error_email_subject(filename):
    "email subject for an error email"
    return u'Error processing digest file: {filename}'.format(filename=filename)


def error_email_body(current_time, error_message=None):
    "body of an error email"
    body = ""
    if error_message:
        body += str(error_message)
    date_format = '%Y-%m-%dT%H:%M:%S.000Z'
    datetime_string = time.strftime(date_format, current_time)
    body += "\nAs at " + datetime_string + "\n"
    body += "\n"
    body += "\n\nSincerely\n\neLife bot"
    return body
