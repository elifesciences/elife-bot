import os
import json
import time
import glob
import re
from collections import OrderedDict
from elifepubmed import generate
from elifepubmed.conf import config, parse_raw_config
import provider.article as articlelib
from provider.sftp import SFTP
from provider import article_processing, email_provider, lax_provider, utils
from provider.storage_provider import storage_context
from activity.objects import Activity


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
        self.statuses = OrderedDict([
            ('generate', None),
            ('approve', None),
            ('upload', None),
            ('publish', None),
            ('outbox', None),
            ('activity', None),
        ])

        self.outbox_s3_key_names = None

        # Track XML files selected for pubmed XML
        self.article_published_file_names = []
        self.article_not_published_file_names = []

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # Get a list of outbox file names always
        self.outbox_s3_key_names = self.get_outbox_s3_key_names()

        # Download the S3 objects
        self.download_files_from_s3_outbox()

        # Generate pubmed XML
        self.statuses['generate'] = self.generate_pubmed_xml()

        # Approve files for publishing
        self.statuses['approve'] = self.approve_for_publishing()

        if self.statuses.get('approve'):
            # Publish files
            try:
                self.statuses['upload'] = self.sftp_files_to_endpoint(
                    from_dir=self.directories.get("TMP_DIR"),
                    file_type="/*.xml")
            except Exception as exception:
                self.logger.exception(str(exception))
                return self.ACTIVITY_PERMANENT_FAILURE

        if self.statuses.get('upload'):
            # Clean up outbox
            print("Moving files from outbox folder to published folder")
            self.clean_outbox()
            self.upload_pubmed_xml_to_s3()
            self.statuses['outbox'] = True
            self.statuses['publish'] = True
        elif self.statuses.get('upload') is False:
            self.statuses['publish'] = False

        # Set the activity status of this activity based on successes
        if self.statuses.get('publish') in (None, True):
            self.statuses['activity'] = True
        else:
            self.statuses['activity'] = False

        # Send email
        # Only if there were files approved for publishing
        if self.article_published_file_names:
            self.send_email()

        # Clean up disk
        self.clean_tmp_dir()

        # return a value based on the activity_status
        if self.statuses.get('activity') is True:
            return True

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

            article = parse_article_xml(xml_file, elifepubmed_config(
                self.settings), self.directories.get("TMP_DIR"), self.logger)

            if article is None:
                self.article_not_published_file_names.append(xml_file)
                continue

            try:
                article = self.enhance_article(article)
            except:
                self.logger.exception(
                    "Exception in enhance_article for xml_file %s in %s" %
                    (xml_file, self.name))
                self.article_not_published_file_names.append(xml_file)
                continue

            if article.is_published is True:
                # generate pubmed deposit
                try:
                    generate.pubmed_xml_to_disk(
                        [article], config_section=self.settings.elifepubmed_config_section)
                except:
                    self.logger.exception(
                        "Exception in generate.pubmed_xml_to_disk for xml_file %s in %s" %
                        (xml_file, self.name))
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
        if not xml_files:
            status = False
        else:
            # Default until full sets of files checker is built
            status = True

        return status

    def sftp_files_to_endpoint(self, from_dir, file_type, sub_dir=None):
        """
        Using the sftp provider module, connect to sftp server and transmit files
        """
        uploadfiles = glob.glob(from_dir + file_type)

        sftp = SFTP(logger=self.logger)
        try:
            sftp_client = sftp.sftp_connect(
                self.settings.PUBMED_SFTP_URI,
                self.settings.PUBMED_SFTP_USERNAME,
                self.settings.PUBMED_SFTP_PASSWORD)
        except Exception as exception:
            self.logger.exception(
                'Failed to connect to SFTP endpoint %s: %s' % (
                    self.settings.PUBMED_SFTP_URI, str(exception)))
            raise

        try:
            sftp.sftp_to_endpoint(
                sftp_client, uploadfiles, self.settings.PUBMED_SFTP_CWD, sub_dir)
        except Exception as exception:
            self.logger.exception('Failed to upload files by SFTP to PubMed: %s' % str(exception))
            raise
        finally:
            sftp.disconnect()

        return True

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
                             article_processing.file_name_from_name(xml_file))
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

        activity_status_text = utils.get_activity_status_text(self.statuses.get('activity'))

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

        activity_status_text = utils.get_activity_status_text(self.statuses.get('activity'))

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"

        body += "activity_status: " + str(self.statuses.get('activity')) + "\n"
        body += "generate_status: " + str(self.statuses.get('generate')) + "\n"
        body += "approve_status: " + str(self.statuses.get('approve')) + "\n"
        body += "upload_status: " + str(self.statuses.get('upload')) + "\n"
        body += "publish_status: " + str(self.statuses.get('publish')) + "\n"
        body += "outbox_status: " + str(self.statuses.get('outbox')) + "\n"

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
        if self.article_published_file_names:
            body += "\n"
            body += "Published files included in pubmed XML: " + "\n"
            for name in self.article_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

        # Report on not published files
        if self.article_not_published_file_names:
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


def elifepubmed_config(settings):
    "parse the config values from the elifepubmed config"
    config.read(settings.elifepubmed_config_file)
    raw_config = config[settings.elifepubmed_config_section]
    return parse_raw_config(raw_config)


def parse_article_xml(xml_file, pubmed_config, tmp_dir, logger):
    """
    Given an article XML files, parse it into an article object
    """
    article = None
    generate.TMP_DIR = tmp_dir
    try:
        # Convert the XML file to article objects
        article_list = generate.build_articles(
            article_xmls=[xml_file],
            build_parts=pubmed_config.get('build_parts'),
            remove_tags=pubmed_config.get('remove_tags'))
        # take the first article from the list
        if article_list:
            article = article_list[0]
    except:
        logger.exception('Exception in parsing article XML %s for PubMed generation' % xml_file)
        article = None

    return article
