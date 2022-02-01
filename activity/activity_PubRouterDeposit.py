import os
import uuid
import json
import time
import glob
import boto3
import boto.s3
from boto.s3.connection import S3Connection

import provider.article as articlelib
from provider import (
    article_processing,
    email_provider,
    lax_provider,
    outbox_provider,
    s3lib,
    utils,
)

from activity.objects import Activity

"""
PubRouterDeposit activity
"""


class activity_PubRouterDeposit(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PubRouterDeposit, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "PubRouterDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download article XML from pub_router outbox, "
            "approve each for publication, and deposit files via FTP to pub router."
        )

        # Set date_stamp
        self.date_stamp = utils.set_datestamp()

        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket

        # Bucket settings for source files workflows
        self.archive_bucket = (
            self.settings.publishing_buckets_prefix + self.settings.archive_bucket
        )
        self.archive_bucket_s3_keys = []

        # Track the success of some steps
        self.activity_status = None
        self.ftp_status = None
        self.outbox_status = None
        self.publish_status = None

        self.outbox_s3_key_names = None

        # Type of FTPArticle workflow to start, will be specified in data
        self.workflow = None

        # Track XML files selected
        self.article_xml_filenames = []
        self.xml_file_to_doi_map = {}
        self.articles = []
        self.articles_approved = []

        # self.article_published_file_names = []
        # self.article_not_published_file_names = []

        self.admin_email_content = ""

        # journal
        self.journal = "elife"

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.workflow = data["data"]["workflow"]
        workflow_folder = outbox_provider.workflow_foldername(self.workflow)
        outbox_folder = outbox_provider.outbox_folder(workflow_folder)
        published_folder = outbox_provider.published_folder(workflow_folder)
        not_published_folder = outbox_provider.not_published_folder(workflow_folder)

        if outbox_folder is None or published_folder is None:
            # Total fail
            return False

        # Download the S3 objects from the outbox
        outbox_s3_key_names = outbox_provider.get_outbox_s3_key_names(
            self.settings, self.publish_bucket, outbox_folder
        )
        outbox_provider.download_files_from_s3_outbox(
            self.settings,
            self.publish_bucket,
            outbox_s3_key_names,
            self.get_tmp_dir(),
            self.logger,
        )
        self.article_xml_filenames = glob.glob(self.get_tmp_dir() + "/*.xml")

        # Get a list of archive zip keys from the bucket for using in approve_articles
        self.archive_bucket_s3_keys = self.get_archive_bucket_s3_keys()

        # Parse the XML
        self.articles = self.parse_article_xml(self.article_xml_filenames)
        # Approve the articles to be sent
        self.articles_approved, remove_doi_list = self.approve_articles(
            self.articles, self.workflow
        )

        for article in self.articles_approved:
            # Start a workflow for each article this is approved to publish
            if self.workflow == "PMC":
                zip_file_name = self.get_latest_archive_zip_name(article)
                starter_status = self.start_pmc_deposit_workflow(
                    article,
                    zip_file_name,
                )
            else:
                starter_status = self.start_ftp_article_workflow(article)

            if starter_status is True:
                if self.logger:
                    log_info = (
                        self.name
                        + " "
                        + self.workflow
                        + " Started a workflow for article: "
                        + article.doi
                    )
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
            else:
                if self.logger:
                    log_info = (
                        self.name
                        + " "
                        + self.workflow
                        + " FAILED to start a workflow for article: "
                        + article.doi
                    )
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)

        # Clean up outbox
        self.logger.info("Moving files from outbox folder to published folder")
        published_file_names = s3_key_names_to_clean(
            outbox_folder, self.articles_approved, self.xml_file_to_doi_map
        )
        date_stamp = utils.set_datestamp()
        to_folder = outbox_provider.get_to_folder_name(published_folder, date_stamp)
        outbox_provider.clean_outbox(
            self.settings,
            self.publish_bucket,
            outbox_folder,
            to_folder,
            published_file_names,
        )
        self.outbox_status = True

        # move file for a remove DOI article out of the outbox folder
        self.logger.info("Moving files from outbox folder to the not_published folder")
        not_published_to_folder = outbox_provider.get_to_folder_name(
            not_published_folder, date_stamp
        )
        not_published_xml_files = []
        for article_doi, file_name in self.xml_file_to_doi_map.items():
            if article_doi in remove_doi_list:
                log_message = (
                    "DOI %s, %s to move file %s to the not_published folder"
                    % (article_doi, self.name, file_name)
                )
                self.logger.info(log_message)
                self.admin_email_content += "\n" + log_message
                not_published_xml_files.append(file_name)
        outbox_provider.clean_outbox(
            self.settings,
            self.publish_bucket,
            outbox_folder,
            not_published_to_folder,
            not_published_xml_files,
        )

        # Send email to admins with the status
        self.activity_status = True
        self.send_admin_email()

        if self.articles_approved:
            self.send_friendly_email(self.workflow, self.articles_approved)

        # Return the activity result, True or False
        result = True

        # Clean up disk
        self.clean_tmp_dir()

        return result

    def start_ftp_article_workflow(self, article):
        """
        In here a new FTPArticle workflow is started for the article object supplied
        """
        starter_status = None

        # Compile the workflow starter parameters
        workflow_id = "FTPArticle_" + self.workflow + "_" + str(article.doi_id)
        workflow_name = "FTPArticle"
        workflow_version = "1"
        # Allow workflow 120 minutes to finish
        execution_start_to_close_timeout = str(60 * 120)

        # Input data
        data = {}
        data["workflow"] = self.workflow
        data["elife_id"] = article.doi_id
        input_json = {}
        input_json["data"] = data
        input_data = json.dumps(input_json)

        kwargs = {
            "domain": self.settings.domain,
            "workflowId": workflow_id,
            "workflowType": {
                "name": workflow_name,
                "version": workflow_version,
            },
            "taskList": {"name": self.settings.default_task_list},
            "executionStartToCloseTimeout": execution_start_to_close_timeout,
            "input": input_data,
        }

        # Connect to SWF
        client = boto3.client(
            "swf",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.swf_region,
        )

        # Try and start a workflow
        try:
            response = self.client.start_workflow_execution(**kwargs)
            starter_status = True
        except Exception as exception:
            # There is already a running workflow with that ID, cannot start another
            message = "%s exception starting workflow %s: %s" % (
                self.name,
                workflow_id,
                str(exception),
            )
            if self.logger:
                self.logger.exception(message)
            starter_status = False

        return starter_status

    def get_archive_bucket_s3_keys(self):
        """
        Get the file name of the most recent archive zip from the archive bucket
        """
        bucket_name = self.archive_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(
            self.settings.aws_access_key_id, self.settings.aws_secret_access_key
        )
        bucket = s3_conn.lookup(bucket_name)

        s3_keys_in_bucket = s3lib.get_s3_keys_from_bucket(bucket=bucket)

        s3_keys = []
        for key in s3_keys_in_bucket:
            s3_keys.append({"name": key.name, "last_modified": key.last_modified})
        return s3_keys

    def get_latest_archive_zip_name(self, article):
        "from the list of s3 keys get the latest archive zip file name"
        return article_processing.latest_archive_zip_revision(
            article.doi_id, self.archive_bucket_s3_keys, self.journal, status="vor"
        )

    def start_pmc_deposit_workflow(self, article, zip_file_name, folder=""):
        """
        Start a PMCDeposit workflow for the article object, by looking up
        the archive zip file for the article DOI
        """
        starter_status = None

        # Compile the workflow starter parameters
        workflow_id = "PMCDeposit_%s" % str(article.doi_id)
        workflow_name = "PMCDeposit"
        workflow_version = "1"
        # Allow workflow 120 minutes to finish
        execution_start_to_close_timeout = None

        # Input data
        data = {}
        data["document"] = zip_file_name
        data["folder"] = folder
        input_json = {}
        input_json["run"] = str(uuid.uuid4())
        input_json["data"] = data
        workflow_input = json.dumps(input_json)

        kwargs = {
            "domain": self.settings.domain,
            "workflowId": workflow_id,
            "workflowType": {
                "name": workflow_name,
                "version": workflow_version,
            },
            "taskList": {"name": self.settings.default_task_list},
            "input": workflow_input,
        }
        if execution_start_to_close_timeout:
            kwargs["executionStartToCloseTimeout"] = execution_start_to_close_timeout

        # Connect to SWF
        client = boto3.client(
            "swf",
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
            region_name=self.settings.swf_region,
        )

        # Try and start a workflow
        try:
            response = self.client.start_workflow_execution(**kwargs)
            starter_status = True
        except Exception as exception:
            # There is already a running workflow with that ID, cannot start another
            message = "%s exception starting workflow %s: %s" % (
                self.name,
                workflow_id,
                str(exception),
            )
            if self.logger:
                self.logger.exception(message)
            starter_status = False

        return starter_status

    def parse_article_xml(self, article_xml_filenames):
        """
        Given a list of article XML filenames,
        parse the files and add the article object to our article map
        """

        articles = []

        for article_xml_filename in article_xml_filenames:

            article = self.create_article()
            article.parse_article_file(article_xml_filename)
            if self.logger:
                log_info = "Parsed " + article.doi_url
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            # Add article object to the object list
            articles.append(article)

            # Add article to the DOI to file name map
            self.xml_file_to_doi_map[article.doi] = article_xml_filename

        return articles

    def create_article(self, doi_id=None):
        """
        Instantiate an article object and optionally populate it with
        data for the doi_id (int) supplied
        """

        # Instantiate a new article object
        article = articlelib.article(self.settings, self.get_tmp_dir())

        if doi_id:
            # Get and parse the article XML for data
            # Convert the doi_id to 5 digit string in case it was an integer
            if isinstance(doi_id, int):
                doi_id = utils.pad_msid(doi_id)
            article_xml_filename = article.download_article_xml_from_s3(doi_id)
            article.parse_article_file(
                self.get_tmp_dir() + os.sep + article_xml_filename
            )
        return article

    def approve_articles(self, articles, workflow):
        """
        Given a list of article objects, approve them for processing
        """

        approved_articles = []

        # Keep track of which articles to remove at the end
        remove_doi_list = []

        # Create a blank article object to use its functions
        blank_article = self.create_article()
        # Remove based on published status

        for article in articles:
            # Check whether the DOI was ever POA
            article.was_ever_poa = lax_provider.was_ever_poa(
                article.doi_id, self.settings
            )

            # Now can check if published
            is_published = lax_provider.published_considering_poa_status(
                article_id=article.doi_id,
                settings=self.settings,
                is_poa=article.is_poa,
                article_was_ever_poa=article.was_ever_poa,
            )
            if is_published is not True:
                if self.logger:
                    log_info = "Removing because it is not published " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                if article.doi not in remove_doi_list:
                    remove_doi_list.append(article.doi)

        # Check article type for OA Switchboard recipient
        if workflow == "OASwitchboard":
            for article in articles:
                if not approve_for_oa_switchboard(article):
                    if self.logger:
                        log_info = (
                            "Removing because the article type is excluded from sending "
                            + article.doi
                        )
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    if article.doi not in remove_doi_list:
                        remove_doi_list.append(article.doi)

        # Check if article is a resupply
        if workflow not in ["CLOCKSS", "OVID", "PMC", "Zendy"]:
            for article in articles:
                was_ever_published = blank_article.was_ever_published(
                    article.doi, workflow
                )
                if was_ever_published is True:
                    if self.logger:
                        log_info = (
                            "Removing because it has been published before "
                            + article.doi
                        )
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    if article.doi not in remove_doi_list:
                        remove_doi_list.append(article.doi)

        # Check a vor archive zip file exists
        if workflow not in ["OVID", "Zendy"]:
            for article in articles:
                # Get the file name of the most recent archive zip from the archive bucket
                zip_file_name = self.get_latest_archive_zip_name(article)
                if not zip_file_name:
                    if self.logger:
                        log_info = (
                            "Removing because there is no archive zip to send "
                            + article.doi
                        )
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    if article.doi not in remove_doi_list:
                        remove_doi_list.append(article.doi)

        # Can remove the articles now without affecting the loops using del
        for article in articles:
            if article.doi not in remove_doi_list:
                approved_articles.append(article)

        return approved_articles, remove_doi_list

    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """
        current_time = time.gmtime()
        date_format = "%Y-%m-%d %H:%M"
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

        subject = email_provider.get_email_subject(
            datetime_string,
            activity_status_text,
            self.name,
            self.settings.domain,
            self.articles_approved,
        )

        body = email_provider.get_email_body_head(self.name, activity_status_text, {})
        body += "\nDetails:\n\n%s\n" % self.admin_email_content
        body += email_provider.get_admin_email_body_foot(
            self.get_activityId(),
            self.get_workflowId(),
            datetime_string,
            self.settings.domain,
        )

        sender_email = self.settings.ses_poa_sender_email

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
                % ("PubRouterDeposit", email)
            )

        return True

    def send_friendly_email(self, workflow, articles_approved):
        """
        After do_activity is finished, send emails to recipients
        including the sucessfully sent article list
        """
        current_time = time.gmtime()

        body = get_friendly_email_body(current_time, articles_approved)
        subject = get_friendly_email_subject(current_time, workflow)
        sender_email = self.settings.ses_poa_sender_email

        # Get pub router recipients
        recipient_email_list = self.get_friendly_email_recipients(workflow)

        # Add admin email recipients
        recipient_email_list += email_provider.list_email_recipients(
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
                "Email sending details: friendly email, email %s, to %s"
                % ("PubRouterDeposit", email)
            )

        return True

    def get_friendly_email_recipients(self, workflow):

        recipient_email_list = []

        recipients = None
        try:
            # Get the email recipient list
            if workflow == "HEFCE":
                recipients = self.settings.HEFCE_EMAIL
            elif workflow == "Cengage":
                recipients = self.settings.CENGAGE_EMAIL
            elif workflow == "GoOA":
                recipients = self.settings.GOOA_EMAIL
            elif workflow == "WoS":
                recipients = self.settings.WOS_EMAIL
            elif workflow == "CNPIEC":
                recipients = self.settings.CNPIEC_EMAIL
            elif workflow == "CNKI":
                recipients = self.settings.CNKI_EMAIL
            elif workflow == "CLOCKSS":
                recipients = self.settings.CLOCKSS_EMAIL
            elif workflow == "OVID":
                recipients = self.settings.OVID_EMAIL
            elif workflow == "Zendy":
                recipients = self.settings.ZENDY_EMAIL
            elif workflow == "OASwitchboard":
                recipients = self.settings.OASWITCHBOARD_EMAIL
        except:
            pass

        if recipients and type(recipients) == list:
            recipient_email_list = recipients
        elif recipients:
            recipient_email_list.append(recipients)

        return recipient_email_list


def get_friendly_email_subject(current_time, workflow):
    """
    Assemble the email subject
    """
    date_format = "%Y-%m-%d"
    datetime_string = time.strftime(date_format, current_time)

    subject = "eLife content for " + workflow + " " + datetime_string

    return subject


def get_friendly_email_body(current_time, approved_articles):
    """
    Format the body of the email
    """

    body = ""

    date_format = "%Y-%m-%d"
    datetime_string = time.strftime(date_format, current_time)

    body += datetime_string
    body += "\n\n"
    body += "eLife is sending content for the following articles"
    body += "\n\n"

    for article in approved_articles:
        body += article.doi
        body += "\n"

    body += "\n\nSincerely\n\neLife bot"

    return body


def approve_for_oa_switchboard(article):
    "check article tyep and display channel to only sent particular types of articles"
    allowed_article_type = "research-article"
    allowed_display_channel_values = [
        "Research Advance",
        "Research Article",
        "Short Report",
        "Tools and Resources",
    ]
    if (
        article
        and hasattr(article, "article_type")
        and hasattr(article, "display_channel")
        and article.article_type == allowed_article_type
        and article.display_channel[0] in allowed_display_channel_values
    ):
        return True
    return False


def s3_key_names_to_clean(outbox_folder, articles_approved, xml_file_to_doi_map):
    """compile a list of S3 key names to clean from the outbox folder"""
    # Concatenate the expected S3 outbox file names
    s3_key_names = []

    # Compile a list of the published file names
    remove_doi_list = []
    processed_file_names = []
    for article in articles_approved:
        remove_doi_list.append(article.doi)

    for key, value in list(xml_file_to_doi_map.items()):
        if key in remove_doi_list:
            processed_file_names.append(value)

    for name in processed_file_names:
        filename = name.split(os.sep)[-1]
        s3_key_name = outbox_folder + filename
        s3_key_names.append(s3_key_name)
    return s3_key_names
