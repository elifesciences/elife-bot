import json
import time
from provider.execution_context import get_session
from provider import cleaner, email_provider, utils
from activity.objects import AcceptedBaseActivity


class activity_EmailAcceptedSubmissionOutput(AcceptedBaseActivity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_EmailAcceptedSubmissionOutput, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "EmailAcceptedSubmissionOutput"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Send an email notification after "
            "accepted submission zip file output is produced."
        )

        # Track the success of some steps
        self.email_status = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        # November 2022 temporary logic to not send email for PRC article ingest
        if session.get_value("prc_status") and not cleaner.PRC_INGEST_SEND_EMAIL:
            self.logger.info(
                "%s for %s, PRC_INGEST_SEND_EMAIL is False so no email will be sent"
                % (self.name, input_filename)
            )
            return True

        # March 2023 also do not send emails for any particular test files
        if (
            session.get_value("prc_status")
            and input_filename in cleaner.PRC_INGEST_IGNORE_SEND_EMAIL
        ):
            self.logger.info(
                "%s, %s is in the PRC_INGEST_IGNORE_SEND_EMAIL list so no email will be sent"
                % (self.name, input_filename)
            )
            return True

        cleaner_log = session.get_value("cleaner_log")

        # format the email body content
        body_content = ""
        comments = cleaner.production_comments(cleaner_log)
        if comments:
            body_content = "Warnings found in the log file for zip file %s\n\n%s" % (
                input_filename,
                "\n".join(comments),
            )
        # Send email
        self.email_status = self.send_email(input_filename, body_content)

        # return a value based on the email_status
        if self.email_status is True:
            return True

        return self.ACTIVITY_PERMANENT_FAILURE

    def send_email(self, output_file, body_content):
        "email the message to the recipients"
        success = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = accepted_submission_email_subject(output_file)
        sender_email = self.settings.accepted_submission_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.accepted_submission_output_recipient_email
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


def accepted_submission_email_subject(output_file):
    "the email subject"
    return "eLife accepted submission: %s" % output_file
