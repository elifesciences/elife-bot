import json
import time
from S3utility.s3_notification_info import parse_activity_data
from provider import email_provider
from activity.objects import Activity


class activity_DecisionLetterReceipt(Activity):
    "DecisionLetterReceipt activity"

    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_DecisionLetterReceipt, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "DecisionLetterReceipt"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Send email as a receipt of a successful decision letter workflow"
        )

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # parse data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # send email
        try:
            self.email_receipt(real_filename)
        except:
            self.logger.exception(
                "Exception raised sending email in %s for file %s."
                % (self.name, real_filename)
            )
            return self.ACTIVITY_TEMPORARY_FAILURE

        return self.ACTIVITY_SUCCESS

    def email_receipt(self, filename):
        "send an email receipt"
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        body = email_provider.simple_email_body(datetime_string)
        subject = receipt_email_subject(filename)
        sender_email = self.settings.decision_letter_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.decision_letter_jats_recipient_email
        )

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_provider.smtp_send(
                connection, sender_email, recipient, email_message, self.logger
            )
        return True


def receipt_email_subject(filename):
    "email subject for a receipt email"
    return u"Decision letter workflow completed! file: {filename}".format(
        filename=filename
    )
