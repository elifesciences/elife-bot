import os
import json
import provider.article as articlelib
from provider.article_processing import download_jats
import provider.email_provider as email_provider
import provider.templates as templatelib
import provider.lax_provider as lax_provider
from provider.storage_provider import storage_context
import provider.glencoe_check as glencoe_check
from activity.objects import Activity


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

        # Templates provider
        self.templates = templatelib.Templates(settings, self.get_tmp_dir())

        # Email types, for sending previews of each template
        self.email_template = 'video_article_publication'

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # get input data
        run = data.get("run")
        article_id = data.get("article_id")
        version = data.get("version")
        status = data.get("status")
        expanded_folder = data.get("expanded_folder")
        run_type = data.get("run_type")

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

        # do not send if silent-correction
        if run_type == "silent-correction":
            self.logger.info(
                ("Silent correction of article %s " +
                 "no email to send in Email Video Article Published ") % article_id)
            self.emit_activity_end_message(article_id, version, run)
            return self.ACTIVITY_SUCCESS

        # do not continue unless it is the first vor version
        first_vor = lax_provider.article_first_by_status(article_id, version, status, self.settings)
        if not first_vor:
            self.logger.info(
                ("Not first VoR version of article %s " +
                 "no email to send in Email Video Article Published ") % article_id)
            self.emit_activity_end_message(article_id, version, run)
            return self.ACTIVITY_SUCCESS

        # download JATS XML from the expanded bucket
        # check if video exists (from article structure)
        expanded_bucket = self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
        has_video = None
        xml_file = download_jats(self.settings, expanded_folder, self.get_tmp_dir(), self.logger)
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
        # Good, we can send emails
        for recipient in recipients:
            send_status = self.send_email(
                email_type, article_object.doi_id, recipient, article_object)
            if not send_status:
                self.logger.info(
                    "Failed to send email for article %s to %s in Email Video Article Published " %
                    (article_id, recipient.get("e_mail")))

        return self.ACTIVITY_SUCCESS

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
        self.templates.download_video_email_templates_from_s3()
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
        """given the email type and recipient, format the email and send it"""

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
                (str(article_id), str(email_type), str(recipient.get("e_mail"))))
            self.logger.info(log_info)
            self.logger.exception(str(exception))
            return False

        try:
            body = self.templates.get_email_body(
                email_type=email_type,
                author=recipient,
                article=article,
                authors=authors,
                format=headers["format"])

            # create the message
            message = email_provider.simple_message(
                headers["sender_email"], recipient.get("e_mail"),
                headers["subject"], body, logger=self.logger)
        except Exception as exception:
            self.logger.exception(
                "Failed to build the email message in send_email: %s" % str(exception))

        try:
            # send the email message
            log_info = ("Sending " + email_type + " type email" +
                        " for article " + str(article_id) +
                        " to recipient_email " + str(recipient.get("e_mail")))
            self.logger.info(log_info)

            details = email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)

            if details.get("error") and int(details.get("error")) > 0:
                self.logger.info(
                    "Failed to send email %s for article %s to %s, details: %s " %
                    (email_type, article_id, recipient.get("e_mail"), str(details)))
                return False

        except Exception as exception:
            self.logger.exception("An exception occurred in send_email: %s" % str(exception))

        return True


def xml_has_video(xml_file):
    "check the XML for videos"
    has_videos = None
    xml_content = None
    with open(xml_file, "r") as open_file:
        xml_content = open_file.read()
        has_videos = glencoe_check.has_videos(xml_content)
    return has_videos
