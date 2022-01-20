import json
import calendar
import time
from datetime import datetime
from activity.objects import Activity

import provider.swfmeta as swfmetalib
from provider import email_provider, utils

"""
AdminEmailHistory activity
"""


class activity_AdminEmailHistory(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_AdminEmailHistory, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "AdminEmailHistory"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Email administrators a workflow history status message."

        # Default time period, in seconds
        self.time_period = 60 * 60 * 4

    def do_activity(self, data=None):
        """
        AdminEmailHistory activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        current_time = time.gmtime()
        current_timestamp = calendar.timegm(current_time)

        workflow_count = self.get_workflow_count_by_closestatus(
            self.time_period, current_timestamp
        )
        history_text = get_history_text(workflow_count)
        body = self.get_email_body(self.time_period, history_text, current_time)
        subject = self.get_email_subject(current_time, workflow_count)
        sender_email = self.settings.ses_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email
        )

        for email in recipient_email_list:
            # send the email by SMTP
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger
            )

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger
            )
            self.logger.info(
                "Email sending details: admin email, email %s, to %s"
                % ("AdminEmailHistory", email)
            )

        return True

    def get_email_subject(self, current_time, workflow_count):
        """
        Assemble the email subject
        """
        date_format = "%Y-%m-%d %H:%M"
        datetime_string = time.strftime(date_format, current_time)

        history_text = ""
        for key in sorted(workflow_count):
            close_status = key
            run_count = workflow_count[key]
            if close_status == "COMPLETED":
                history_text += " c:" + str(run_count)
            elif close_status == "FAILED":
                history_text += " f:" + str(run_count)
            elif close_status == "CANCELED":
                pass
            elif close_status == "TERMINATED":
                pass
            elif close_status == "CONTINUED_AS_NEW":
                pass
            elif close_status == "TIMED_OUT":
                history_text += " to:" + str(run_count)

        subject = (
            "eLife SWF "
            + datetime_string
            + history_text
            + ", domain: "
            + self.settings.domain
        )

        return subject

    def get_email_body(self, time_period, history_text, current_time):
        """
        Format the body of the email
        """

        body = ""

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, current_time)

        body = "A short history of workflow executions\n"
        body += "As at " + datetime_string + "\n"
        body += "Time period: " + str(time_period) + " seconds" + "\n"
        body += "Domain: " + self.settings.domain + "\n"
        body += history_text
        body += "\n\nSincerely\n\neLife bot"

        return body

    def get_workflow_count_by_closestatus(self, time_period, current_timestamp):
        """
        Given the time_period in seconds, and the current_timestamp
        use the SWFMeta provider to count closed workflows
        """

        close_status_list = [
            "COMPLETED",
            "FAILED",
            "CANCELED",
            "TERMINATED",
            "CONTINUED_AS_NEW",
            "TIMED_OUT",
        ]

        swfmeta = swfmetalib.SWFMeta(self.settings)
        swfmeta.connect()

        # convert timestamp to datetime objects
        start_latest_date = datetime.utcfromtimestamp(current_timestamp)
        start_oldest_date = datetime.utcfromtimestamp(
            swfmetalib.utctimestamp(start_latest_date) - time_period
        )

        workflow_count = {}

        for close_status in close_status_list:
            count = swfmeta.get_closed_workflow_execution_count(
                domain=self.settings.domain,
                start_oldest_date=start_oldest_date,
                start_latest_date=start_latest_date,
                close_status=close_status,
            )
            run_count = None
            try:
                run_count = count["count"]
            except:
                run_count = None

            if run_count:
                workflow_count[close_status] = run_count
            else:
                workflow_count[close_status] = 0

        return workflow_count


def get_history_text(workflow_count):
    """
    Given a dictionary of closed workflow executions and their count,
    get the workflow history text to include in the email body
    If no workflow_count is supplied, get it from the object time_period in seconds
    """

    history_text = ""

    # Concatenate the message
    for key in sorted(workflow_count):
        close_status = key
        run_count = workflow_count[key]

        history_text = history_text + "\n" + close_status + ": " + str(run_count)

    if history_text == "":
        history_text = None
    return history_text
