import json
import time
from provider.execution_context import get_session
from provider import email_provider, utils
from activity.objects import Activity


class activity_EmailMecaOutput(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_EmailMecaOutput, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "EmailMecaOutput"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Send an email notification after "
            "a MECA file is ingested and an output MECA file is produced"
        )

        # Track the success of some steps
        self.email_status = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        version_doi = session.get_value("version_doi")
        # get log messages from the session
        log_messages = session.get_value("log_messages")

        # format the email body content
        body_content = ""
        if log_messages:
            body_content = "Log messages for version DOI %s\n\n%s" % (
                version_doi,
                "\n%s" % utils.bytes_decode(log_messages),
            )
        # Send email
        self.email_status = self.send_email(version_doi, body_content)

        # return a value based on the email_status
        if self.email_status is True:
            return self.ACTIVITY_SUCCESS

        return self.ACTIVITY_PERMANENT_FAILURE

    def send_email(self, version_doi, body_content):
        "email the message to the recipients"
        success = True

        # error status from keywords in body_content:
        error = None
        if "ValidateJatsDtd, validation error" in body_content:
            error = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = meca_email_subject(version_doi, self.settings, error)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email
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


def meca_email_subject(version_doi, settings=None, error=None):
    "the email subject"
    subject_prefix = ""
    if utils.settings_environment(settings) == "continuumtest":
        subject_prefix = "TEST "
    extra = ""
    if error:
        extra = "Error in "
    return "%seLife ingest MECA: %s%s" % (subject_prefix, extra, version_doi)
