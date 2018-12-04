import boto.swf
import json
import calendar
import time
import boto.ses
import boto.s3
from boto.s3.connection import S3Connection
import provider.simpleDB as dblib
from activity.objects import Activity

"""
SendQueuedEmail activity
"""

class activity_SendQueuedEmail(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_SendQueuedEmail, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "SendQueuedEmail"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Send email in the email queue."

        # Data provider
        self.db = dblib.SimpleDB(settings)

        # Default limit of emails per activity
        self.limit = 100

        # Default rate limit
        self.rate_limit_per_sec = 10

        # S3 bucket where email body content is stored
        self.email_body_bucket = settings.bot_bucket

    def do_activity(self, data=None):
        """
        SendQueuedEmail activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)

        domain_name = "EmailQueue"

        limit = self.limit

        # The current time in date string format
        date_format = "%Y-%m-%dT%H:%M:%S.000Z"
        current_time = time.gmtime()
        date_scheduled_before = time.strftime(date_format, current_time)

        # Connect to DB
        db_conn = self.db.connect()

        email_items = self.db.elife_get_email_queue_items(
            query_type="items",
            limit=limit,
            date_scheduled_before=date_scheduled_before)

        email_count = 0
        for e in email_items:

            # Wait if the rate limit is reached
            if (self.rate_limit_per_sec and email_count > 0
                    and email_count % self.rate_limit_per_sec == 0):
                if self.logger:
                    self.logger.info('SendQueuedEmail waiting 1 second after sending %s emails'
                                     % str(self.rate_limit_per_sec))
                time.sleep(1)

            item_name = e.name
            item_attrs = {}

            body = None
            # Get the email body from S3
            try:
                body = self.get_email_body(e["body_s3key"])
            except KeyError:
                # Missing a body, skip it
                continue
            # Check for a blank body
            if body is None:
                continue

            try:
                result = self.send_email(
                    sender_email=e["sender_email"],
                    recipient_email=e["recipient_email"],
                    subject=e["subject"],
                    body=body,
                    format=e["format"])
            except KeyError:
                # Missing an expected value, handle exception and
                #  continue the loop
                if self.logger:
                    self.logger.exception("KeyError exception attempting to send email %s", e)
                continue
            except boto.ses.exceptions.SESIllegalAddressError:
                if self.logger:
                    self.logger.exception("SESIllegalAddressError exception attempting to send email %s", e)
                continue
            except Exception as err:
                # unhandled exception
                if self.logger:
                    self.logger.exception("unhandled exception %r attempting to send email %s", err, e)
                raise

            if result is True:
                item_attrs["date_sent_timestamp"] = calendar.timegm(time.gmtime())
                item_attrs["sent_status"] = True
                self.db.put_attributes(domain_name, item_name, item_attrs)
            elif result is False:
                # Did not send correctly
                item_attrs["sent_status"] = False
                self.db.put_attributes(domain_name, item_name, item_attrs)

            # Increment the counter
            email_count += 1

        return True

    def send_email(self, sender_email, recipient_email, subject, body, format="text"):
        """
        Using Amazon SES service
        """

        ses_conn = boto.ses.connect_to_region(
            self.settings.simpledb_region,
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key)

        try:
            ses_conn.send_email(
                source=sender_email,
                to_addresses=recipient_email,
                subject=subject,
                body=body,
                format=format)
            return True
        except boto.ses.exceptions.SESAddressNotVerifiedError:
            # For now, try to ask the recipient to verify
            ses_conn.verify_email_address(recipient_email)
            # Also verify the sender, that could be the problem
            ses_conn.verify_email_address(sender_email)
            return False

    def get_email_body(self, body_s3key):
        """
        From the S3 bucket, get the object content for the body_s3key key
        """

        body = None

        # Connect to S3 and the bucket
        bucket_name = self.email_body_bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        # Head request on the key
        s3key = bucket.get_key(body_s3key)
        if s3key:
            # The key exists, get the contents
            body = s3key.get_contents_as_string()

        return body
