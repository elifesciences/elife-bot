import os
import boto.swf
import json
import time
import arrow
from collections import namedtuple
import requests
import glob
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib
import provider.article as articlelib
import provider.s3lib as s3lib
from provider import lax_provider
from provider import utils
from elifecrossref import generate
from elifecrossref.conf import config, parse_raw_config
from elifearticle.article import ArticleDate

"""
DepositCrossref activity
"""

class activity_DepositCrossref(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "DepositCrossref"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = ("Download article XML from crossref outbox, " +
                            "generate crossref XML, and deposit with crossref.")

        # Local directory settings
        self.TMP_DIR = "tmp_dir"
        self.INPUT_DIR = "input_dir"

        # Create output directories
        self.create_activity_directories()
        self.date_stamp = self.set_datestamp()

        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)

        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "crossref/outbox/"
        self.published_folder = "crossref/published/"

        # Track the success of some steps
        self.activity_status = None
        self.generate_status = None
        self.approve_status = None
        self.outbox_status = None
        self.publish_status = None

        # HTTP requests status
        self.http_request_status_code = []
        self.http_request_status_text = []

        self.outbox_s3_key_names = None

        # Track XML files selected for pubmed XML
        self.article_published_file_names = []
        self.article_not_published_file_names = []

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Download the S3 objects
        self.download_files_from_s3_outbox()

        # Generate crossref XML
        self.generate_status = self.generate_crossref_xml()

        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()

        if self.approve_status is True:
            try:
                # Publish files
                self.publish_status = self.deposit_files_to_endpoint(
                    file_type="/*.xml",
                    sub_dir=os.path.join(self.get_tmp_dir(), self.TMP_DIR))
            except:
                self.publish_status = False

            if self.publish_status is True:
                # Clean up outbox
                print "Moving files from outbox folder to published folder"
                self.clean_outbox()
                self.upload_crossref_xml_to_s3()
                self.outbox_status = True

        # Set the activity status of this activity based on successes
        if self.publish_status is not False and self.generate_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Send email
        # Only if there were files approved for publishing
        if len(self.article_published_file_names) > 0:
            self.add_email_to_queue()

        # Return the activity result, True or False
        result = True

        return result

    def set_datestamp(self):
        a = arrow.utcnow()
        date_stamp = (str(a.datetime.year) + str(a.datetime.month).zfill(2) +
                      str(a.datetime.day).zfill(2))
        return date_stamp

    def download_files_from_s3_outbox(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml and .pdf files to be bundled.
        """
        file_extensions = []
        file_extensions.append(".xml")

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=self.outbox_folder,
            file_extensions=file_extensions)

        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            # Save .xml and .pdf to different folders
            if re.search(".*\\.xml$", name):
                dirname = os.path.join(self.get_tmp_dir(), self.INPUT_DIR)

            filename_plus_path = dirname + os.sep + filename
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()

    def elifecrossref_config(self, config_section):
        "parse the config values from the elifecrossref config"
        config.read(self.settings.elifecrossref_config_file)
        raw_config = config[config_section]
        return parse_raw_config(raw_config)

    def article_first_pub_date(self, article):
        "find the first article pub date from the list of crossref config pub_date_types"
        pub_date = None
        crossref_config = self.elifecrossref_config(self.settings.elifecrossref_config_section)
        if crossref_config.get('pub_date_types'):
            # check for any useable pub date
            for pub_date_type in crossref_config.get('pub_date_types'):
                if article.get_date(pub_date_type):
                    pub_date = article.get_date(pub_date_type)
                    break
        return pub_date

    def parse_article_xml(self, article_xml_files):
        """
        Given a list of article XML files, parse them into objects
        and save the file name for later use
        """

        # For each article XML file, parse it and save the filename for later
        articles = []
        for article_xml in article_xml_files:
            article = None
            article_list = None
            article_xml_list = [article_xml]
            try:
                # Convert the XML files to article objects
                generate.TMP_DIR = os.path.join(self.get_tmp_dir(), self.TMP_DIR)
                article_list = generate.build_articles(article_xml_list)
                article = article_list[0]
            except:
                continue

            # Check for a pub date
            article_pub_date = self.article_first_pub_date(article)
            # if no date was found then look for one on Lax
            if not article_pub_date:
                lax_pub_date = lax_provider.article_publication_date(article.manuscript, self.settings, self.logger)
                if lax_pub_date:
                    date_struct = time.strptime(lax_pub_date, utils.S3_DATE_FORMAT)
                    crossref_config = self.elifecrossref_config(self.settings.elifecrossref_config_section)
                    pub_date_object = ArticleDate(crossref_config.get('pub_date_types')[0], date_struct)
                    article.add_date(pub_date_object)

            # Check for a version number
            if not article.version:
                lax_version = lax_provider.article_highest_version(article.manuscript, self.settings)
                if lax_version:
                    article.version = lax_version

            if article:
                articles.append(article)

        return articles

    def generate_crossref_xml(self):
        """
        Using the POA generateCrossrefXml module
        """
        article_xml_files = glob.glob(os.path.join(self.get_tmp_dir(), self.INPUT_DIR) + "/*.xml")

        for xml_file in article_xml_files:
            generate_status = True

            # Convert the single value to a list for processing
            xml_files = [xml_file]
            article_list = self.parse_article_xml(xml_files)

            if len(article_list) == 0:
                self.article_not_published_file_names.append(xml_file)
                continue
            else:
                article = article_list[0]

            if self.approve_to_generate(article) is not True:
                generate_status = False
            else:
                try:
                    # Will write the XML to the TMP_DIR
                    generate.crossref_xml_to_disk(
                        article_list, config_section=self.settings.elifecrossref_config_section)
                except:
                    generate_status = False

            if generate_status is True:
                # Add filename to the list of published files
                self.article_published_file_names.append(xml_file)
            else:
                # Add the file to the list of not published articles, may be used later
                self.article_not_published_file_names.append(xml_file)

        # Any files generated is a sucess, even if one failed
        return True

    def approve_to_generate(self, article):
        """
        Given an article object, decide if crossref deposit should be
        generated from it
        """
        approved = None
        # Embargo if the pub date is in the future
        article_pub_date = self.article_first_pub_date(article)
        if article_pub_date:
            now_date = time.gmtime()
            if article_pub_date.date < now_date:
                approved = True
            else:
                # Pub date is later than now, do not approve
                approved = False
        else:
            # No pub date, then we approve it
            approved = True

        return approved


    def approve_for_publishing(self):
        """
        Final checks before publishing files to the endpoint
        """
        status = None

        # Check for empty directory
        article_xml_files = glob.glob(os.path.join(self.get_tmp_dir(), self.INPUT_DIR) + "/*.xml")
        if len(article_xml_files) <= 0:
            status = False
        else:
            # Default until full sets of files checker is built
            status = True

        return status

    def deposit_files_to_endpoint(self, file_type, sub_dir=None):
        """
        Using an HTTP POST, deposit the file to the endpoint
        """

        # Default return status
        status = True

        url = self.settings.crossref_url
        payload = {'operation': 'doMDUpload',
                   'login_id': self.settings.crossref_login_id,
                   'login_passwd': self.settings.crossref_login_passwd
                  }

        # Crossref XML, should be only one but check for multiple
        xml_files = glob.glob(sub_dir + file_type)

        for xml_file in xml_files:
            files = {'file': open(xml_file, 'rb')}

            r = requests.post(url, data=payload, files=files)

            # Check for good HTTP status code
            if r.status_code != 200:
                status = False
            #print r.text
            self.http_request_status_text.append("XML file: " + xml_file)
            self.http_request_status_text.append("HTTP status: " + str(r.status_code))
            self.http_request_status_text.append("HTTP response: " + r.text)

        return status

    def get_outbox_s3_key_names(self, force=None):
        """
        Separately get a list of S3 key names form the outbox
        for reporting purposes, excluding the outbox folder itself
        """

        # Return cached values if available
        if self.outbox_s3_key_names and not force:
            return self.outbox_s3_key_names

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=self.outbox_folder)

        # Remove the outbox_folder from the list, if present
        try:
            s3_key_names.remove(self.outbox_folder)
        except:
            pass

        self.outbox_s3_key_names = s3_key_names

        return self.outbox_s3_key_names

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
        # Save the list of outbox contents to report on later
        outbox_s3_key_names = self.get_outbox_s3_key_names()

        to_folder = self.get_to_folder_name()

        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        # Concatenate the expected S3 outbox file names
        s3_key_names = []
        for name in self.article_published_file_names:
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


    def upload_crossref_xml_to_s3(self):
        """
        Upload a copy of the crossref XML to S3 for reference
        """
        xml_files = glob.glob(os.path.join(self.get_tmp_dir(), self.TMP_DIR) + "/*.xml")

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        date_folder_name = self.date_stamp
        s3_folder_name = self.published_folder + date_folder_name + "/" + "batch/"

        for xml_file in xml_files:
            s3key = boto.s3.key.Key(bucket)
            s3key.key = s3_folder_name + xml_file.split(os.sep)[-1]
            s3key.set_contents_from_filename(xml_file, replace=True)

    def add_email_to_queue(self):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        # Connect to DB
        db_conn = self.db.connect()

        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()

        body = self.get_email_body(current_time)
        subject = self.get_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if type(self.settings.ses_admin_email) == list:
            for email in self.settings.ses_admin_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_admin_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            self.db.elife_add_email_to_email_queue(
                recipient_email=email,
                sender_email=sender_email,
                email_type="DepositCrossref",
                format="text",
                subject=subject,
                body=body)

        return True

    def get_activity_status_text(self, activity_status):
        """
        Given the activity status boolean, return a human
        readable text version
        """
        if activity_status is True:
            activity_status_text = "Success!"
        else:
            activity_status_text = "FAILED."

        return activity_status_text

    def get_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        # Count the files moved from the outbox, the files that were processed
        files_count = 0
        outbox_s3_key_names = self.get_outbox_s3_key_names()
        if outbox_s3_key_names:
            files_count = len(outbox_s3_key_names)

        subject = (self.name + " " + activity_status_text +
                   " files: " + str(files_count) +
                   ", " + datetime_string +
                   ", eLife SWF domain: " + self.settings.domain)

        return subject

    def get_email_body(self, current_time):
        """
        Format the body of the email
        """

        body = ""

        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"

        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "generate_status: " + str(self.generate_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "publish_status: " + str(self.publish_status) + "\n"
        body += "outbox_status: " + str(self.outbox_status) + "\n"

        body += "\n"
        body += "Outbox files: " + "\n"

        outbox_s3_key_names = self.get_outbox_s3_key_names()
        files_count = 0
        if outbox_s3_key_names:
            files_count = len(outbox_s3_key_names)
        if files_count > 0:
            for name in outbox_s3_key_names:
                body += name + "\n"
        else:
            body += "No files in outbox." + "\n"

        # Report on published files
        if len(self.article_published_file_names) > 0:
            body += "\n"
            body += "Published files generated crossref XML: " + "\n"
            for name in self.article_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

        # Report on not published files
        if len(self.article_not_published_file_names) > 0:
            body += "\n"
            body += "Files not approved or failed crossref XML: " + "\n"
            for name in self.article_not_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

        body += "\n"
        body += "-------------------------------\n"
        body += "HTTP deposit details: " + "\n"
        for code in self.http_request_status_code:
            body += "Status code: " + str(code) + "\n"
        for text in self.http_request_status_text:
            body += str(text) + "\n"

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


    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """

        try:
            os.mkdir(os.path.join(self.get_tmp_dir(), self.TMP_DIR))
            os.mkdir(os.path.join(self.get_tmp_dir(), self.INPUT_DIR))
        except:
            pass
