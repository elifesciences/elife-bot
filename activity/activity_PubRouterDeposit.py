import os
import uuid
import boto.swf
import json
import time
import arrow

import boto.s3
from boto.s3.connection import S3Connection

import provider.article as articlelib
from provider import email_provider, lax_provider, s3lib, utils

import dateutil.parser
from activity.objects import Activity

"""
PubRouterDeposit activity
"""

class activity_PubRouterDeposit(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PubRouterDeposit, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PubRouterDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = ("Download article XML from pub_router outbox, \
                            approve each for publication, and deposit files via FTP to pub router.")

        # Set date_stamp
        self.date_stamp = utils.set_datestamp()

        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = None
        self.published_folder = None

        # Bucket settings for source files of FTPArticle workflows
        self.pmc_zip_bucket = settings.poa_packaging_bucket
        self.pmc_zip_folder = "pmc/zip/"

        # Bucket settings for source files of PMCDeposit workflows
        self.archive_bucket = self.settings.publishing_buckets_prefix + self.settings.archive_bucket

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

        #self.article_published_file_names = []
        #self.article_not_published_file_names = []

        self.admin_email_content = ''

        # journal
        self.journal = 'elife'

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.workflow = data["data"]["workflow"]
        self.outbox_folder = self.get_outbox_folder(self.workflow)
        self.published_folder = self.get_published_folder(self.workflow)

        if self.outbox_folder is None or self.published_folder is None:
            # Total fail
            return False

        # Download the S3 objects from the outbox
        self.article_xml_filenames = self.download_files_from_s3_outbox()
        # Parse the XML
        self.articles = self.parse_article_xml(self.article_xml_filenames)
        # Approve the articles to be sent
        self.articles_approved = self.approve_articles(self.articles, self.workflow)


        for article in self.articles_approved:
            # Start a workflow for each article this is approved to publish
            if self.workflow == "PMC":
                zip_file_name = self.archive_zip_file_name(article)
                starter_status = self.start_pmc_deposit_workflow(article, zip_file_name,)
            else:
                starter_status = self.start_ftp_article_workflow(article)

            if starter_status is True:
                if self.logger:
                    log_info = (self.name + " " + self.workflow +
                                " Started a workflow for article: " + article.doi)
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
            else:
                if self.logger:
                    log_info = (self.name + " " + self.workflow +
                                " FAILED to start a workflow for article: " + article.doi)
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)

        # Clean up outbox
        print("Moving files from outbox folder to published folder")
        self.clean_outbox()
        self.outbox_status = True

        # Send email to admins with the status
        self.activity_status = True
        self.send_admin_email()

        if len(self.articles_approved) > 0:
            self.send_friendly_email(self.workflow, self.articles_approved)

        # Return the activity result, True or False
        result = True

        # Clean up disk
        self.clean_tmp_dir()

        return result

    def get_outbox_folder(self, workflow):
        """
        S3 outbox, where files to be processed are
        """
        if workflow == "HEFCE":
            return "pub_router/outbox/"
        elif workflow == "Cengage":
            return "cengage/outbox/"
        elif workflow == "GoOA":
            return "gooa/outbox/"
        elif workflow == "WoS":
            return "wos/outbox/"
        elif workflow == "PMC":
            return "pmc/outbox/"
        elif workflow == "CNPIEC":
            return "cnpiec/outbox/"
        elif workflow == "CNKI":
            return "cnki/outbox/"
        elif workflow == "CLOCKSS":
            return "clockss/outbox/"
        elif workflow == "OVID":
            return "ovid/outbox/"
        elif workflow == "Zendy":
            return "zendy/outbox/"

        return None

    def get_published_folder(self, workflow):
        """
        S3 published folder, where processed files are copied to
        """
        if workflow == "HEFCE":
            return "pub_router/published/"
        elif workflow == "Cengage":
            return "cengage/published/"
        elif workflow == "GoOA":
            return "gooa/published/"
        elif workflow == "WoS":
            return "wos/published/"
        elif workflow == "PMC":
            return "pmc/published/"
        elif workflow == "CNPIEC":
            return "cnpiec/published/"
        elif workflow == "CNKI":
            return "cnki/published/"
        elif workflow == "CLOCKSS":
            return "clockss/published/"
        elif workflow == "OVID":
            return "ovid/published/"
        elif workflow == "Zendy":
            return "zendy/published/"

        return None

    def start_ftp_article_workflow(self, article):
        """
        In here a new FTPArticle workflow is started for the article object supplied
        """
        starter_status = None

        # Compile the workflow starter parameters
        workflow_id = "FTPArticle_" + self.workflow + "_" + str(article.doi_id)
        workflow_name = "FTPArticle"
        workflow_version = "1"
        child_policy = None
        # Allow workflow 120 minutes to finish
        execution_start_to_close_timeout = str(60*120)

        # Input data
        data = {}
        data['workflow'] = self.workflow
        data['elife_id'] = article.doi_id
        input_json = {}
        input_json['data'] = data
        input = json.dumps(input_json)

        # Connect to SWF
        conn = boto.swf.layer1.Layer1(self.settings.aws_access_key_id,
                                      self.settings.aws_secret_access_key)

        # Try and start a workflow
        try:
            response = conn.start_workflow_execution(self.settings.domain, workflow_id,
                                                     workflow_name, workflow_version,
                                                     self.settings.default_task_list,
                                                     child_policy,
                                                     execution_start_to_close_timeout, input)
            starter_status = True
        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = ('SWFWorkflowExecutionAlreadyStartedError: ' +
                       'There is already a running workflow with ID %s' % workflow_id)
            print(message)
            if self.logger:
                self.logger.info(message)
            starter_status = False

        return starter_status

    def archive_zip_file_name(self, article, status='vor'):
        """
        Get the file name of the most recent archive zip from the archive bucket
        """
        bucket_name = self.archive_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_keys_in_bucket = s3lib.get_s3_keys_from_bucket(bucket=bucket)

        s3_keys = []
        for key in s3_keys_in_bucket:
            s3_keys.append({"name": key.name, "last_modified": key.last_modified})

        return self.latest_archive_zip_revision(article.doi_id, s3_keys, self.journal, status)

    def latest_archive_zip_revision(self, doi_id, s3_keys, journal, status):
        """
        Get the most recent version of the article zip file from the
        list of bucket key names
        """
        s3_key_name = None

        name_prefix_to_match = (journal + '-' + str(doi_id).zfill(5)
                                + '-' + status + '-v')

        highest = 0
        for key in s3_keys:
            if key["name"].startswith(name_prefix_to_match):
                version_and_date = None
                try:
                    parts = key["name"].split(name_prefix_to_match)
                    version = parts[1].split('-')[0]
                    date_formatted = dateutil.parser.parse(key["last_modified"])
                    date_part = date_formatted.strftime('%Y%m%d%H%M%S')
                    version_and_date = int(version + date_part)
                except:
                    pass
                if version_and_date and version_and_date > highest:
                    s3_key_name = key["name"]
                    highest = version_and_date

        return s3_key_name


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
        child_policy = None
        # Allow workflow 120 minutes to finish
        execution_start_to_close_timeout = None

        # Input data
        data = {}
        data['document'] = zip_file_name
        data['folder'] = folder
        input_json = {}
        input_json['run'] = str(uuid.uuid4())
        input_json['data'] = data
        workflow_input = json.dumps(input_json)

        # Connect to SWF
        conn = boto.swf.layer1.Layer1(self.settings.aws_access_key_id,
                                      self.settings.aws_secret_access_key)

        # Try and start a workflow
        try:
            response = conn.start_workflow_execution(self.settings.domain, workflow_id,
                                                     workflow_name, workflow_version,
                                                     self.settings.default_task_list,
                                                     child_policy,
                                                     execution_start_to_close_timeout,
                                                     workflow_input)
            starter_status = True
        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = ('SWFWorkflowExecutionAlreadyStartedError: ' +
                       'There is already a running workflow with ID %s' % workflow_id)
            print(message)
            if self.logger:
                self.logger.info(message)
            starter_status = False

        return starter_status

    def download_files_from_s3_outbox(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml to be processed
        """
        filenames = []

        file_extensions = []
        file_extensions.append(".xml")

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=self.outbox_folder,
            file_extensions=file_extensions)

        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            # Download to the activity temp directory
            dirname = self.get_tmp_dir()

            filename_plus_path = dirname + os.sep + filename

            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()

            filenames.append(filename_plus_path)

        return filenames

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
            if type(doi_id) == int:
                doi_id = str(doi_id).zfill(5)
            article_xml_filename = article.download_article_xml_from_s3(doi_id)
            article.parse_article_file(self.get_tmp_dir() + os.sep + article_xml_filename)
        return article

    def approve_articles(self, articles, workflow):
        """
        Given a list of article objects, approve them for processing
        """

        approved_articles = []

        # Keep track of which articles to remove at the end
        remove_article_doi = []

        # Create a blank article object to use its functions
        blank_article = self.create_article()
        # Remove based on published status

        for article in articles:
            # Check whether the DOI was ever POA
            article.was_ever_poa = lax_provider.was_ever_poa(article.doi_id, self.settings)

            # Now can check if published
            is_published = lax_provider.published_considering_poa_status(
                article_id=article.doi_id,
                settings=self.settings,
                is_poa=article.is_poa,
                was_ever_poa=article.was_ever_poa)
            if is_published is not True:
                if self.logger:
                    log_info = "Removing because it is not published " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                remove_article_doi.append(article.doi)

        # Check if article is a resupply
        if workflow not in ["CLOCKSS", "OVID", "PMC", "Zendy"]:
            for article in articles:
                was_ever_published = blank_article.was_ever_published(article.doi, workflow)
                if was_ever_published is True:
                    if self.logger:
                        log_info = "Removing because it has been published before " + article.doi
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    remove_article_doi.append(article.doi)

        # Check if a PMC zip file exists for this article
        if workflow not in ["OVID", "PMC", "Zendy"]:
            for article in articles:
                if not self.does_source_zip_exist_from_s3(doi_id=article.doi_id):
                    if self.logger:
                        log_info = ("Removing because there is no PMC zip file to send " +
                                    article.doi)
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    remove_article_doi.append(article.doi)

        # For PMC workflows, check the archive zip file exists
        if workflow == 'PMC':
            for article in articles:
                zip_file_name = self.archive_zip_file_name(article)
                if not zip_file_name:
                    if self.logger:
                        log_info = ("Removing because there is no archive zip for PMC to send " +
                                    article.doi)
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)
                    remove_article_doi.append(article.doi)

        # Can remove the articles now without affecting the loops using del
        for article in articles:
            if article.doi not in remove_article_doi:
                approved_articles.append(article)

        return approved_articles

    def get_to_folder_name(self):
        """
        From the date_stamp
        return the S3 folder name to save published files into
        """
        to_folder = None

        date_folder_name = self.date_stamp
        to_folder = self.published_folder + date_folder_name + "/"

        return to_folder

    def clean_outbox(self):
        """
        Clean out the S3 outbox folder
        """

        to_folder = self.get_to_folder_name()

        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        # Concatenate the expected S3 outbox file names
        s3_key_names = []

        # Compile a list of the published file names
        remove_doi_list = []
        processed_file_names = []
        for article in self.articles_approved:
            remove_doi_list.append(article.doi)

        for k, v in list(self.xml_file_to_doi_map.items()):
            if k in remove_doi_list:
                processed_file_names.append(v)

        for name in processed_file_names:
            filename = name.split(os.sep)[-1]
            s3_key_name = self.outbox_folder + filename
            s3_key_names.append(s3_key_name)

        for name in s3_key_names:
            # Download objects from S3 and save to disk

            # Do not delete the from_folder itself, if it is in the list
            if name != self.outbox_folder:
                filename = name.split("/")[-1]
                new_s3_key_name = to_folder + filename

                # First copy
                new_s3_key = None
                try:
                    new_s3_key = bucket.copy_key(new_s3_key_name, bucket_name, name)
                except:
                    pass

                # Then delete the old key if successful
                if isinstance(new_s3_key, boto.s3.key.Key):
                    old_s3_key = bucket.get_key(name)
                    old_s3_key.delete()

    def does_source_zip_exist_from_s3(self, doi_id):
        """

        """
        bucket_name = self.pmc_zip_bucket
        prefix = self.pmc_zip_folder

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=prefix)

        s3_key_name = s3lib.latest_pmc_zip_revision(doi_id, s3_key_names)

        if s3_key_name:
            return True
        else:
            return False


    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """
        current_time = time.gmtime()

        body = self.get_admin_email_body(current_time)
        subject = self.get_admin_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email)

        for email in recipient_email_list:
            # send the email by SMTP
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger)

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)
            self.logger.info('Email sending details: admin email, email %s, to %s' %
                             ("PubRouterDeposit", email))

        return True

    def send_friendly_email(self, workflow, articles_approved):
        """
        After do_activity is finished, send emails to recipients
        including the sucessfully sent article list
        """
        current_time = time.gmtime()

        body = self.get_friendly_email_body(current_time, workflow, articles_approved)
        subject = self.get_friendly_email_subject(current_time, workflow)
        sender_email = self.settings.ses_poa_sender_email

        # Get pub router recipients
        recipient_email_list = self.get_friendly_email_recipients(workflow)

        # Add admin email recipients
        recipient_email_list += email_provider.list_email_recipients(
            self.settings.ses_admin_email)

        for email in recipient_email_list:
            # send the email by SMTP
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger)

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)
            self.logger.info('Email sending details: friendly email, email %s, to %s' %
                             ("PubRouterDeposit", email))

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
        except:
            pass

        if recipients and type(recipients) == list:
            recipient_email_list = recipients
        elif recipients:
            recipient_email_list.append(recipients)

        return recipient_email_list

    def get_admin_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

        subject = (self.name + " " + str(self.workflow) + " " + activity_status_text +
                   ", " + datetime_string +
                   ", eLife SWF domain: " + self.settings.domain)

        return subject

    def get_admin_email_body(self, current_time):
        """
        Format the body of the email
        """

        body = ""

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

        # Bulk of body
        body += "Workflow type:" + str(self.workflow)
        body += "\n"
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"
        body += "Details:" + "\n"
        body += "\n"
        body += self.admin_email_content + "\n"
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

    def get_friendly_email_subject(self, current_time, workflow):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d'
        datetime_string = time.strftime(date_format, current_time)

        subject = ("eLife content for " + workflow + " " +  datetime_string)

        return subject

    def get_friendly_email_body(self, current_time, workflow, approved_articles):
        """
        Format the body of the email
        """

        body = ""

        date_format = '%Y-%m-%d'
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
