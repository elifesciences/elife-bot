import os
import json
import time
from digestparser import output
import digestparser.utils as digest_utils
from S3utility.s3_notification_info import parse_activity_data
from provider import digest_provider, download_helper, email_provider, utils
from activity.objects import Activity


class activity_EmailDigest(Activity):
    "EmailDigest activity"

    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_EmailDigest, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "EmailDigest"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download digest file input from the bucket, parse it, generate the "
            + "output and send it in an email to recipients."
        )

        # Track some values
        self.input_file = None
        self.digest = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Track the success of some steps
        self.activity_status = None
        self.build_status = None
        self.generate_status = None
        self.approve_status = None
        self.email_status = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # parse the data with the digest_provider
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )

        # Parse input and build digest
        self.build_status, self.digest = digest_provider.build_digest(
            self.input_file,
            self.directories.get("TEMP_DIR"),
            self.logger,
            self.digest_config,
        )

        # Generate output
        self.generate_status, output_file = self.generate_output(self.digest)

        if self.generate_status is True:
            self.activity_status = True

        # Approve files for emailing
        self.approve_status, error_messages = digest_provider.validate_digest(
            self.digest
        )

        if self.approve_status is True and self.generate_status is True:
            # Email file
            self.email_status = self.email_digest(self.digest, output_file)

        # return a value based on the activity_status
        if self.activity_status is True:
            return True

        return self.ACTIVITY_PERMANENT_FAILURE

    def output_path(self, output_dir, file_name):
        """for python 3 cast file_name to str so it can be joined with the path value"""
        return os.path.join(output_dir, str(file_name))

    def generate_output(self, digest_content):
        "From the parsed digest content generate the output"
        if not digest_content:
            return False, None
        file_name = output_file_name(digest_content, self.digest_config)
        self.logger.info("EmailDigest output file_name: %s", file_name)
        full_file_name = self.output_path(
            self.directories.get("OUTPUT_DIR"), str(file_name)
        )
        self.logger.info("EmailDigest output full_file_name: %s", full_file_name)
        try:
            output_file = output.digest_docx(digest_content, full_file_name)
        except UnicodeEncodeError as exception:
            self.logger.exception(
                "EmailDigest generate_output exception. Message: %s", exception
            )
            return False, None
        return True, output_file

    def email_digest(self, digest_content, output_file):
        "email the digest as an attachment to the recipients"
        success = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string)
        subject = success_email_subject(digest_content)
        sender_email = self.settings.digest_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.digest_docx_recipient_email
        )

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            email_provider.add_attachment(email_message, output_file)
            # send the email
            email_success = email_provider.smtp_send(
                connection, sender_email, recipient, email_message, self.logger
            )
            if not email_success:
                # for now any failure in sending a mail return False
                success = False
        return success


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
        doi = getattr(digest_content, "doi")
        msid = doi.split(".")[-1]
    except AttributeError:
        msid = None
    return u"Digest: {author}_{msid:0>5}".format(
        author=digest_content.author, msid=str(msid)
    )
