import os
import json
import time
import boto.swf
from digestparser import build, output
import activity
from S3utility.s3_notification_info import S3NotificationInfo
from provider.storage_provider import storage_context
import provider.email_provider as email_provider


class activity_EmailDigest(activity.activity):
    "EmailDigest activity"
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

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

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        info = S3NotificationInfo.from_dict(data)
        filename = info.file_name[info.file_name.rfind('/')+1:]
        bucket_name = info.bucket_name
        bucket_folder = None
        if filename:
            bucket_folder = info.file_name.split(filename)[0]

        # Download from S3
        self.input_file = self.download_digest_from_s3(filename, bucket_name, bucket_folder)

        # Parse input and build digest
        self.build_status, self.digest = self.build_digest(self.input_file)

        # Generate output
        self.generate_status, output_file = self.generate_output(self.digest)

        if self.generate_status is True:
            self.activity_status = True

        # Approve files for emailing
        # todo!!!
        self.approve_status = True

        if self.approve_status is True:
            # Email files
            if self.generate_status is True:
                self.email_status = self.email_digest(self.digest, output_file)
            else:
                self.email_status = self.email_error_report()

        # return a value based on the activity_status
        if self.activity_status is True:
            return True

        return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def download_digest_from_s3(self, filename, bucket_name, bucket_folder):
        "Connect to the S3 bucket and download the input"
        if not filename or not bucket_name or bucket_folder is None:
            return None
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + bucket_folder
        storage_resource_origin = orig_resource + '/' + filename
        dirname = self.input_dir
        filename_plus_path = dirname + os.sep + filename
        with open(filename_plus_path, 'wb') as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        return filename_plus_path

    def build_digest(self, input_file):
        "Parse input and build a Digest object"
        if not input_file:
            return False, None
        digest = build.build_digest(input_file, self.temp_dir)
        return True, digest

    def generate_output(self, digest_content):
        "From the parsed digest content generate the output"
        if not digest_content:
            return False, None
        file_name = output_file_name(digest_content)
        output_file = output.digest_docx(digest_content, file_name, self.output_dir)
        return True, output_file

    def email_digest(self, digest_content, output_file):
        "email the digest as an attachment to the recipients"
        success = True

        current_time = time.gmtime()
        body = success_email_body(current_time)
        subject = success_email_subject(digest_content)
        sender_email = self.settings.ses_digest_sender_email

        recipient_email_list = list_email_recipients(self.settings.ses_digest_recipient_email)

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

    def email_error_report(self):
        "todo!!"
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


def output_file_name(digest_content):
    "from the digest content return the file name for the DOCX output"
    if not digest_content:
        return
    try:
        doi = getattr(digest_content, 'doi')
        msid = doi.split(".")[-1]
    except AttributeError:
        msid = None
    return '{author}_{msid:0>5}.docx'.format(author=digest_content.author, msid=msid)


def success_email_subject(digest_content):
    "the email subject"
    if not digest_content:
        return
    try:
        doi = getattr(digest_content, 'doi')
        msid = doi.split(".")[-1]
    except AttributeError:
        msid = None
    return 'Digest: {author}_{msid}'.format(author=digest_content.author, msid=msid)


def list_email_recipients(email_list):
    "return a list of email recipients from a string or list input"
    recipient_email_list = []
    # Handle multiple recipients, if specified
    if isinstance(email_list, list):
        for email in email_list:
            recipient_email_list.append(email)
    else:
        recipient_email_list.append(email_list)
    return recipient_email_list


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
