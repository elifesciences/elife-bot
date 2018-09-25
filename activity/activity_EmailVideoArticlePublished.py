import os
import json
import provider.simpleDB as dblib
import provider.article as articlelib
import provider.templates as templatelib
import provider.lax_provider as lax_provider
from provider.storage_provider import storage_context
import provider.glencoe_check as glencoe_check
from .activity import Activity


class activity_EmailVideoArticlePublished(Activity):
    "EmailVideoArticlePublished activity"

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_EmailVideoArticlePublished, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "EmailVideoArticlePublished"
        self.pretty_name = "Email Video Article Published"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Send email when an article containing a video is published."

        # Data provider
        self.database = dblib.SimpleDB(settings)

        # Templates provider
        self.templates = templatelib.Templates(settings, self.get_tmp_dir())

        # Default is do not send duplicate emails
        self.allow_duplicates = False

        # Email types, for sending previews of each template
        self.email_template = 'video_article_publication'

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # get input data
        success, run, article_id, version, status, expanded_folder = self.parse_data(data)

        # emit start message
        success = self.emit_activity_start_message(article_id, version, run)
        if success is not True:
            self.logger.error("Failed to emit a start message in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # do not send if poa
        if status == "poa":
            self.logger.info(
                "PoA article %s no email to send in Email Video Article Published " % article_id)
            self.emit_activity_end_message(article_id, version, run)
            return self.ACTIVITY_SUCCESS

        # download JATS XML from the expanded bucket
        # check if video exists (from article structure)
        expanded_bucket = self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        has_video = None
        xml_file = self.download_xml(
            expanded_bucket, expanded_folder, version, self.get_tmp_dir())
        if xml_file:
            has_video = xml_has_video(xml_file)
        if not has_video:
            self.logger.info(
                "Article %s has no video in Email Video Article Published " % article_id)
            self.emit_activity_end_message(article_id, version, run)
            return self.ACTIVITY_SUCCESS
        # video exists, get recipient(s) from settings
        recipients = self.choose_recipients()

        # queue emails for sending
        article_object = self.parse_article_xml(xml_file)
        # email type or template to send
        email_type = "video_article_publication"
        templates_downloaded = self.download_templates()
        if not templates_downloaded:
            self.logger.error(
                "Could not download email templates sending %s in Email Video Article Published " %
                article_id)
            return self.ACTIVITY_PERMANENT_FAILURE
        # Good, we can add emails to the queue
        # Connect to DB
        self.database.connect()
        for recipient in recipients:
            send = None
            if self.allow_duplicates is True:
                send = True
            else:
                is_duplicate = self.is_duplicate_email(
                    article_id, email_type, recipient.get("e_mail"))
                if not is_duplicate:
                    send = True
            if not send:
                self.logger.info(
                    "Will not send email for article %s to %s in Email Video Article Published " %
                    (article_id, recipient.get("e_mail")))
            send_status = self.send_email(
                email_type, article_object.doi_id, recipient, article_object)
            if not send_status:
                self.logger.info(
                    "Failed to send email for article %s to %s in Email Video Article Published " %
                    (article_id, recipient.get("e_mail")))

        return self.ACTIVITY_SUCCESS

    def parse_data(self, data):
        "extract individual values from the activity data"
        run = None
        article_id = None
        version = None
        status = None
        expanded_folder = None
        success = None
        try:
            run = data.get("run")
            article_id = data.get("article_id")
            version = data.get("version")
            status = data.get("status")
            expanded_folder = data.get("expanded_folder")
            success = True
        except (TypeError, KeyError) as exception:
            self.logger.exception("Exception when getting the session for Starting ingest " +
                                  " digest to endpoint. Details: %s" % str(exception))
        return success, run, article_id, version, status, expanded_folder

    def download_xml(self, expanded_bucket, expanded_folder, version, to_dir):
        "download JATS XML from the expanded bucket"
        xml_file = None
        self.logger.info("expanded_bucket: " + expanded_bucket)
        xml_filename = lax_provider.get_xml_file_name(
            self.settings, expanded_folder, expanded_bucket, version)
        if xml_filename is None:
            raise RuntimeError("No xml_filename found.")
        xml_origin = "".join((self.settings.storage_provider, "://", expanded_bucket, "/",
                              expanded_folder, "/", xml_filename))
        storage = storage_context(self.settings)
        filename_plus_path = os.path.join(to_dir, xml_filename)
        with open(filename_plus_path, "wb") as open_file:
            storage.get_resource_to_file(xml_origin, open_file)
            xml_file = filename_plus_path
        return xml_file

    def choose_recipients(self):
        "recipients of the email from the settings"
        recipients = []

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if isinstance(self.settings.email_video_recipient_email, list):
            for email in self.settings.email_video_recipient_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.email_video_recipient_email)

        for recipient_email in recipient_email_list:
            feature_author = {}
            feature_author["first_nm"] = "Features"
            feature_author["e_mail"] = recipient_email
            recipients.append(feature_author)
        return recipients

    def parse_article_xml(self, xml_file):
        """
        Given a list of article XML filenames,
        parse the files and add the article object to our article map
        """
        article_object = articlelib.article(self.settings, self.get_tmp_dir())
        article_object.parse_article_file(xml_file)
        if self.logger:
            self.logger.info("Parsed %s" % article_object.doi_url)
        return article_object

    def download_templates(self):
        """
        Download the email templates from s3
        """
        # Prepare email templates
        self.templates.download_email_templates_from_s3()
        if self.templates.email_templates_warmed is not True:
            if self.logger:
                log_info = 'EmailVideoArticlePublished email templates did not warm successfully'
                self.logger.info(log_info)
            # Stop now! Return False if we do not have the necessary files
            return False
        else:
            if self.logger:
                log_info = 'EmailVideoArticlePublished email templates warmed'
                self.logger.info(log_info)
            return True

    def send_email(self, email_type, article_id, recipient, article, authors=None):
        "given the email type and recipient, format the email and add it to the queue"

        if recipient is None:
            return False
        if "e_mail" not in recipient:
            return False
        if recipient.get("e_mail") is None:
            return False
        if recipient.get("e_mail") is not None and str(recipient.get("e_mail")).strip() == "":
            return False

        # First process the headers
        try:
            headers = self.templates.get_email_headers(
                email_type=email_type,
                author=recipient,
                article=article,
                format="html")
        except Exception as exception:
            log_info = (
                'Failed to load email headers for: doi_id: %s email_type: %s recipient_email: %s' %
                (str(article_id), str(email_type), str(recipient.e_mail)))
            self.logger.info(log_info)
            self.logger.exception(str(exception))
            return False

        # Get the article published date timestamp
        date_scheduled_timestamp = 0

        try:
            # Queue the email
            if self.logger:
                log_info = ("Sending " + email_type + " type email" +
                            " for article " + str(article_id) +
                            " to recipient_email " + str(recipient.e_mail))
                self.logger.info(log_info)

            self.queue_email(
                email_type=email_type,
                recipient=recipient,
                headers=headers,
                article=article,
                authors=authors,
                doi_id=article_id,
                date_scheduled_timestamp=date_scheduled_timestamp,
                email_format="html")
            return True

        except Exception:
            if self.logger:
                self.logger.exception("An error has occurred on send_email method")
                pass

    def queue_email(self, email_type, recipient, headers, article, authors, doi_id,
                    date_scheduled_timestamp, email_format="html"):
        """
        Format the email body and add it to the live queue
        Only call this to send actual emails!
        """
        body = self.templates.get_email_body(
            email_type=email_type,
            author=recipient,
            article=article,
            authors=authors,
            format=email_format)

        # Add the email to the email queue
        self.database.elife_add_email_to_email_queue(
            recipient_email=recipient.e_mail,
            sender_email=headers["sender_email"],
            email_type=headers["email_type"],
            format=headers["format"],
            subject=headers["subject"],
            body=body,
            doi_id=doi_id,
            date_scheduled_timestamp=date_scheduled_timestamp)

    def is_duplicate_email(self, doi_id, email_type, recipient_email):
        """
        Use the SimpleDB provider to count the number of emails
        in the queue for the particular combination of variables
        to determine whether we should not send an email twice
        Default: return None
          No matching emails: return False
          Is a matching email in the queue: return True
        """
        duplicate = None
        try:
            count = 0

            # Count all emails of all sent statuses
            for sent_status in True, False, None:
                result_list = self.database.elife_get_email_queue_items(
                    query_type="count",
                    doi_id=doi_id,
                    email_type=email_type,
                    recipient_email=recipient_email,
                    sent_status=sent_status
                )

                count_result = result_list[0]
                count += int(count_result["Count"])

            # Now make a decision on how many emails counted
            if count > 0:
                duplicate = True
            elif count == 0:
                duplicate = False

        except:
            # Do nothing, we will return the default
            pass

        return duplicate


def xml_has_video(xml_file):
    "check the XML for videos"
    has_videos = None
    xml_content = None
    with open(xml_file, "rb") as open_file:
        xml_content = open_file.read()
        has_videos = glencoe_check.has_videos(xml_content)
    return has_videos
