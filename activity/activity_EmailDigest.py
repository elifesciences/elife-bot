import os
import boto.swf
import json
import time
import activity
from S3utility.s3_notification_info import S3NotificationInfo
import provider.simpleDB as dblib
from provider.storage_provider import storage_context
from digestparser import parse

"""
EmailDigest activity
"""

class activity_EmailDigest(activity.activity):

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

        # Local directory settings
        self.temp_dir = "tmp_dir"
        self.input_dir = "input_dir"

        # Create output directories
        self.create_activity_directories()

        # Data provider where email body is saved
        self.db_provider = dblib.SimpleDB(settings)

        # Track the success of some steps
        self.activity_status = None
        self.parse_status = None
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

        # Parse input
        self.parse_status, digest_content = self.parse_digest(self.input_file)

        # Generate output
        # todo!!!
        self.generate_status = self.generate_output(digest_content)

        if self.generate_status is True:
            self.activity_status = True

        # Approve files for emailing
        # todo!!!
        self.approve_status = True

        if self.approve_status is True:
            # Email files
            # todo!!!!
            self.email_status = self.add_email_to_queue()

        # return a value based on the activity_status
        if self.activity_status is True:
            return True
        else:
            return activity.activity.ACTIVITY_PERMANENT_FAILURE


    def download_digest_from_s3(self, filename, bucket_name, bucket_folder):
        "Connect to the S3 bucket and download the input"
        if not filename or not bucket_name or bucket_folder is None:
            return None
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + bucket_folder
        storage_resource_origin = orig_resource + '/' + filename
        dirname = os.path.join(self.get_tmp_dir(), self.input_dir)
        filename_plus_path = dirname + os.sep + filename
        with open(filename_plus_path, 'wb') as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        return filename_plus_path


    def parse_digest(self, input_file):
        "Parse input into an object"
        # todo!!!
        if not input_file:
            return False, None
        return True, 'fake_digest_content'


    def generate_output(self, digest_content):
        "From the parsed digest content generate the output"
        if not digest_content:
            return False
        return True


    def add_email_to_queue(self):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        # Connect to DB
        self.db_provider.connect()

        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()

        body = self.get_email_body(current_time)
        subject = self.get_email_subject(current_time)
        sender_email = self.settings.ses_digest_sender_email

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if isinstance(self.settings.ses_digest_recipient_email, list):
            for email in self.settings.ses_digest_recipient_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_digest_recipient_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            self.db_provider.elife_add_email_to_email_queue(
                recipient_email=email,
                sender_email=sender_email,
                email_type="EmailDigest",
                format="text",
                subject=subject,
                body=body)

        return True


    def get_activity_status_text(self, activity_status):
        """
        Given the activity status boolean, return a human
        readable text version
        """
        if activity_status is True:
            activity_status_text = "Success!"
        else:
            activity_status_text = "FAILED."

        return activity_status_text


    def get_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        subject = (self.name + " " + activity_status_text +
                   ", " + datetime_string +
                   ", eLife SWF domain: " + self.settings.domain)

        return subject


    def get_email_body(self, current_time):
        """
        Format the body of the email
        """
        body = ""

        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"

        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "parse_status: " + str(self.parse_status) + "\n"
        body += "generate_status: " + str(self.generate_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "email_status: " + str(self.email_status) + "\n"

        body += "\n"

        body += "\n"
        body += "-------------------------------\n"
        body += "SWF workflow details: " + "\n"
        body += "activityId: " + str(self.get_activityId()) + "\n"
        body += "As part of workflowId: " + str(self.get_workflowId()) + "\n"
        body += "As at " + datetime_string + "\n"
        body += "Domain: " + self.settings.domain + "\n"

        body += "\n"

        body += "\n\nSincerely\n\neLife bot"

        return body


    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [
                os.path.join(self.get_tmp_dir(), self.temp_dir),
                os.path.join(self.get_tmp_dir(), self.input_dir)
            ]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
