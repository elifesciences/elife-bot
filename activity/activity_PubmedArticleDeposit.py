import os
import boto.swf
import json
import importlib
import time
import arrow
import glob
import re
import requests
from collections import namedtuple

import provider.article as articlelib
from provider.ftp import FTP
from provider import email_provider, lax_provider, utils
from provider.storage_provider import storage_context
from elifepubmed import generate
from elifepubmed.conf import config, parse_raw_config
from activity.objects import Activity

"""
PubmedArticleDeposit activity
"""

class activity_PubmedArticleDeposit(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PubmedArticleDeposit, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PubmedArticleDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = ("Download article XML from pubmed outbox, generate pubmed " +
                            "article XML, and deposit with pubmed.")

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        self.date_stamp = utils.set_datestamp()

        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "pubmed/outbox"
        self.published_folder = "pubmed/published"

        # Track the success of some steps
        self.activity_status = None
        self.generate_status = None
        self.approve_status = None
        self.ftp_status = None
        self.outbox_status = None
        self.publish_status = None

        self.outbox_s3_key_names = None

        # Track XML files selected for pubmed XML
        self.article_published_file_names = []
        self.article_not_published_file_names = []

        # Load the config
        self.pubmed_config = self.elifepubmed_config(self.settings.elifepubmed_config_section)

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # Get a list of outbox file names always
        self.outbox_s3_key_names = self.get_outbox_s3_key_names()

        # Download the S3 objects
        self.download_files_from_s3_outbox()

        # Generate pubmed XML
        self.generate_status = self.generate_pubmed_xml()

        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()

        if self.approve_status is True:
            # Publish files
            self.ftp_status = self.ftp_files_to_endpoint(
                from_dir=self.directories.get("TMP_DIR"),
                file_type="/*.xml")

        if self.ftp_status is True:
            # Clean up outbox
            print("Moving files from outbox folder to published folder")
            self.clean_outbox()
            self.upload_pubmed_xml_to_s3()
            self.outbox_status = True
            self.publish_status = True
        elif self.ftp_status is False:
            self.publish_status = False

        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Send email
        # Only if there were files approved for publishing
        if len(self.article_published_file_names) > 0:
            self.send_email()

        # Clean up disk
        self.clean_tmp_dir()

        # return a value based on the activity_status
        if self.activity_status is True:
            return True
        else:
            return self.ACTIVITY_PERMANENT_FAILURE

    def download_files_from_s3_outbox(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml files
        """
        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + self.outbox_folder
        files_in_bucket = storage.list_resources(orig_resource)

        for name in files_in_bucket:
            # Download objects from S3 and save to disk
            # Only need to copy .xml files
            if not re.search(".*\\.xml$", name):
                continue
            filename = name.split("/")[-1]
            dirname = self.directories.get("INPUT_DIR")
            if dirname:
                filename_plus_path = dirname + os.sep + filename
                with open(filename_plus_path, 'wb') as open_file:
                    storage_resource_origin = orig_resource + '/' + name
                    storage.get_resource_to_file(storage_resource_origin, open_file)


    def elifepubmed_config(self, config_section):
        "parse the config values from the elifepubmed config"
        config.read(self.settings.elifepubmed_config_file)
        raw_config = config[config_section]
        return parse_raw_config(raw_config)

    def parse_article_xml(self, xml_file):
        """
        Given an article XML files, parse it into an article object
        """
        article = None
        generate.TMP_DIR = self.directories.get("TMP_DIR")
        try:
            # Convert the XML file to article objects
            article_list = generate.build_articles(
                article_xmls=[xml_file],
                build_parts=self.pubmed_config.get('build_parts'),
                remove_tags=self.pubmed_config.get('remove_tags'))
            # take the first article from the list
            if article_list:
                article = article_list[0]
        except:
            article = None

        return article

    def get_article_version_from_lax(self, article_id):
        """
        Temporary fix to set the version of the article if available
        """
        version = lax_provider.article_highest_version(article_id, self.settings)
        if version is None:
            return "-1"
        return version

    def enhance_article(self, article):
        "set additional details on the article object from Lax data or other sources"

        article.was_ever_poa = lax_provider.was_ever_poa(article.manuscript, self.settings)

        # Check if each article is published
        article.is_published = lax_provider.published_considering_poa_status(
            article_id=article.manuscript,
            settings=self.settings,
            is_poa=article.is_poa,
            was_ever_poa=article.was_ever_poa)

        if not article.version:
            article.version = self.get_article_version_from_lax(article.manuscript)

        return article

    def generate_pubmed_xml(self):
        """
        Using the POA generatePubMedXml module
        """
        generate_status = None
        article_xml_files = glob.glob(self.directories.get("INPUT_DIR") + "/*.xml")

        for xml_file in article_xml_files:
            generate_status = True

            article = self.parse_article_xml(xml_file)

            if article is None:
                self.article_not_published_file_names.append(xml_file)
                continue

            article = self.enhance_article(article)

            if article.is_published is True:
                # generate pubmed deposit
                try:
                    generate.pubmed_xml_to_disk(
                        [article], config_section=self.settings.elifepubmed_config_section)
                except:
                    generate_status = False
            else:
                generate_status = False

            if generate_status is True:
                # Add filename to the list of published files
                self.article_published_file_names.append(xml_file)
            else:
                # Add the file to the list of not published articles, may be used later
                self.article_not_published_file_names.append(xml_file)

        return generate_status

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the endpoint
        """
        status = None

        # Check for empty directory
        xml_files = glob.glob(self.directories.get("TMP_DIR") + "/*.xml")
        if len(xml_files) <= 0:
            status = False
        else:
            # Default until full sets of files checker is built
            status = True

        return status

    def get_filename_from_path(self, f, extension):
        """
        Get a filename minus the supplied file extension
        and without any folder or path
        """
        filename = f.split(extension)[0]
        # Remove path if present
        try:
            filename = filename.split(os.sep)[-1]
        except:
            pass

        return filename

    def ftp_files_to_endpoint(self, from_dir, file_type):
        """
        FTP files to endpoint
        as specified by the file_type to use in the glob
        e.g. "/*.zip"
        """
        ftp_status = None
        try:
            ftp_provider = FTP()
            ftp_instance = ftp_provider.ftp_connect(
                uri=self.settings.PUBMED_FTP_URI,
                username=self.settings.PUBMED_FTP_USERNAME,
                password=self.settings.PUBMED_FTP_PASSWORD
            )
            # collect the list of files
            zipfiles = glob.glob(from_dir + file_type)
            # transfer them by FTP to the endpoint
            ftp_provider.ftp_to_endpoint(
                ftp_instance=ftp_instance,
                uploadfiles=zipfiles,
                sub_dir_list=[self.settings.PUBMED_FTP_CWD])
            # disconnect the FTP connection
            ftp_provider.ftp_disconnect(ftp_instance)
            ftp_status = True
        except:
            ftp_status = False
        return ftp_status

    def get_outbox_s3_key_names(self, force=None):
        """
        Separately get a list of S3 key names from the outbox
        for reporting purposes, excluding the outbox folder itself
        """

        # Return cached values if available
        if self.outbox_s3_key_names and not force:
            return self.outbox_s3_key_names

        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + self.outbox_folder
        files_in_bucket = storage.list_resources(orig_resource)
        # add the prefix back to the file name to set the value
        # and ignore the original folder name
        self.outbox_s3_key_names = [self.outbox_folder + '/' + filename
                                    for filename in files_in_bucket
                                    if filename != '']

        return self.outbox_s3_key_names

    def get_to_folder_name(self):
        """
        From the date_stamp
        return the S3 folder name to save published files into
        """
        to_folder = None

        date_folder_name = self.date_stamp
        to_folder = self.published_folder + "/" + date_folder_name + "/"

        return to_folder

    def clean_outbox(self):
        """
        Clean out the S3 outbox folder
        """
        # Save the list of outbox contents to report on later
        outbox_s3_key_names = self.get_outbox_s3_key_names()

        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket
        to_folder = self.get_to_folder_name()

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"

        # Concatenate the expected S3 outbox file names
        s3_key_names = []
        for name in self.article_published_file_names:
            filename = name.split(os.sep)[-1]
            s3_key_name = self.outbox_folder + '/' + filename
            s3_key_names.append(s3_key_name)

        for name in s3_key_names:
            filename = name.split("/")[-1]
            orig_resource = storage_provider + bucket_name + "/" + name
            dest_resource = storage_provider + bucket_name + "/" + to_folder + filename
            storage.copy_resource(orig_resource, dest_resource)
            # Then delete the old key
            storage.delete_resource(orig_resource)

    def upload_pubmed_xml_to_s3(self):
        """
        Upload a copy of the pubmed XML to S3 for reference
        """
        xml_files = glob.glob(self.directories.get("TMP_DIR") + "/*.xml")

        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"

        date_folder_name = self.date_stamp
        s3_folder_name = self.published_folder + '/' + date_folder_name + "/" + "batch"

        for xml_file in xml_files:
            resource_dest = (storage_provider + bucket_name + "/" +
                             s3_folder_name + "/" +
                             self.get_filename_from_path(xml_file, '.xml') + '.xml')
            storage.set_resource_from_filename(resource_dest, xml_file)

    def send_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        current_time = time.gmtime()

        body = self.get_email_body(current_time)
        subject = self.get_email_subject(current_time)
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
                             ("PubmedArticleDeposit", email))

        return True

    def get_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

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

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"

        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "generate_status: " + str(self.generate_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "ftp_status: " + str(self.ftp_status) + "\n"
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
            body += "Published files included in pubmed XML: " + "\n"
            for name in self.article_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

        # Report on not published files
        if len(self.article_not_published_file_names) > 0:
            body += "\n"
            body += "Files in pubmed outbox not yet published: " + "\n"
            for name in self.article_not_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

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
