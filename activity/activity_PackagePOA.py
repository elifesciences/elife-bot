import os
import json
import time
import zipfile
import glob
import shutil
import importlib
from collections import OrderedDict
from xml.parsers.expat import ExpatError
from ejpcsvparser import parse
from jatsgenerator import generate
from jatsgenerator import conf as jats_conf
from packagepoa import transform
from packagepoa import conf as poa_conf
from elifearticle.article import ArticleDate
import provider.ejp as ejplib
import provider.lax_provider as lax_provider
from provider.storage_provider import storage_context
from provider import email_provider, utils
from activity.objects import Activity


class activity_PackagePOA(Activity):
    "PackagePOA activity"
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PackagePOA, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PackagePOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = "Process POA zip file input, repackage, and save to S3."

        # Activity directories
        self.directories = OrderedDict([
            ("EJP_INPUT", os.path.join(self.get_tmp_dir(), "ejp_input")),
            ("XML_OUTPUT", os.path.join(self.get_tmp_dir(), "generated_xml_output")),
            ("CSV", os.path.join(self.get_tmp_dir(), "csv_data")),
            ("CSV_TMP", os.path.join(self.get_tmp_dir(), "csv_data", "tmp")),
            ("DECAPITATE_PDF", os.path.join(self.get_tmp_dir(), "decapitate_pdf_dir")),
            ("POA_TMP", os.path.join(self.get_tmp_dir(), "tmp")),
            ("OUTPUT", os.path.join(self.get_tmp_dir(), "output_dir"))
        ])

        # Create an EJP provider to access S3 bucket holding CSV files
        self.ejp = ejplib.EJP(settings, self.get_tmp_dir())
        self.ejp_bucket = self.settings.ejp_bucket

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "outbox/"

        # Some values to set later
        self.document = None
        self.poa_zip_filename = None
        self.doi = None

        # Capture errors from generating XML
        self.error_count = None
        self.error_messages = None

        # Track the success of some steps
        self.activity_status = None
        self.approve_status = None
        self.process_status = None
        self.generate_xml_status = None
        self.pdf_decap_status = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        # Download the S3 object
        self.document = data["data"]["document"]

        # Download POA zip file
        self.poa_zip_filename = self.download_poa_zip(self.document)

        # Get the DOI from the zip file
        self.doi = get_doi_from_zip_file(self.poa_zip_filename)
        doi_id = utils.msid_from_doi(self.doi)
        self.logger.info('DOI: %s' % doi_id)

        # Approve the DOI for packaging
        self.approve_status = approve_for_packaging(doi_id)

        if self.approve_status is False:
            # Bad. Fail the activity
            self.activity_status = False

        else:
            # Good, continue

            # Transform zip file
            self.process_status = self.process_poa_zipfile(self.poa_zip_filename)
            self.logger.info('Process status: %s' % self.process_status)
            self.pdf_decap_status = self.check_pdf_decap_failure()
            self.logger.info('PDF decapitation status: %s' % self.pdf_decap_status)

            # Set the DOI and generate XML
            self.download_latest_csv()
            pub_date = self.get_pub_date(doi_id)
            volume = utils.volume_from_pub_date(pub_date)
            try:
                self.generate_xml(doi_id, pub_date, volume)
                self.generate_xml_status = True
            except Exception as exception:
                self.logger.exception('Exception in generate_xml: %s' % str(exception))
                self.generate_xml_status = False
            self.logger.info('XML generation status: %s' % self.generate_xml_status)

            # Copy finished files to S3 outbox
            self.copy_files_to_s3_outbox()

            # Set the activity status of this activity based on successes
            self.activity_status = bool(self.process_status is True and
                                        self.pdf_decap_status is True and
                                        self.generate_xml_status is True)

        # Send email
        self.send_email()

        # Return the activity result, True or False
        result = True

        if self.activity_status is True:
            self.clean_tmp_dir()

        # reload the ejpcsvparser/csv_data.py module to clear cached CSV data
        importlib.reload(parse.data)

        return result

    def clean_tmp_dir(self):
        "custom cleaning of temp directory in order to retain some files for debugging purposes"
        keep_dirs = ['CSV', 'CSV_TMP']
        for dir_name, dir_path in self.directories.items():
            if dir_name in keep_dirs or not os.path.exists(dir_path):
                continue
            shutil.rmtree(dir_path)

    def get_pub_date(self, doi_id):
        # Get the date for the first version
        date_struct = None
        date_str = lax_provider.article_publication_date(
            utils.pad_msid(doi_id), self.settings, self.logger)

        if date_str is not None:
            date_struct = time.strptime(date_str, "%Y%m%d000000")
        else:
            # Use current date
            date_struct = time.gmtime()

        return date_struct

    def download_poa_zip(self, document):
        """
        Given the s3 object name as document, download it from the
        POA delivery bucket and save file to disk in the EJP_INPUT dir
        """
        bucket_name = self.settings.poa_bucket
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/"

        storage_resource_origin = orig_resource + document
        filename_plus_path = os.path.join(self.directories.get("EJP_INPUT"), document)
        try:
            with open(filename_plus_path, 'wb') as open_file:
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except IOError:
            return None
        return filename_plus_path

    def packagepoa_config(self, config_section):
        "parse the config values from the jatsgenerator config"
        return poa_conf.parse_raw_config(poa_conf.raw_config(
            config_section,
            self.settings.packagepoa_config_file))

    def process_poa_zipfile(self, poa_zip_filename):
        """
        Using the POA transform-ejp-zip-to-hw-zip module
        """
        if poa_zip_filename is None:
            return False
        poa_config = self.packagepoa_config(self.settings.packagepoa_config_section)
        # override the output directories
        poa_config['output_dir'] = self.directories.get("OUTPUT")
        poa_config['decapitate_pdf_dir'] = self.directories.get("DECAPITATE_PDF")
        poa_config['tmp_dir'] = self.directories.get("POA_TMP")
        try:
            transform.process_zipfile(
                zipfile_name=poa_zip_filename,
                poa_config=poa_config
            )
            return True
        except zipfile.BadZipfile:
            return False

    def check_pdf_decap_failure(self):
        """
        After processing the zipfile there should be a PDF present, as a
        result of decapitating the file. If not, return false
        """
        pdf_files = glob.glob(self.directories.get("DECAPITATE_PDF") + "/*.pdf")
        if not pdf_files:
            return False
        return True

    def download_latest_csv(self):
        """
        Download the latest CSV files from S3, rename them, and
        save to the CSV directory
        """

        # Key: File types, value: file to save as to disk
        file_types = {
            "poa_author": "poa_author.csv",
            "poa_license": "poa_license.csv",
            "poa_manuscript": "poa_manuscript.csv",
            "poa_received": "poa_received.csv",
            "poa_subject_area": "poa_subject_area.csv",
            "poa_research_organism": "poa_research_organism.csv",
            "poa_abstract": "poa_abstract.csv",
            "poa_title": "poa_title.csv",
            "poa_keywords": "poa_keywords.csv",
            "poa_group_authors": "poa_group_authors.csv",
            "poa_datasets": "poa_datasets.csv",
            "poa_funding": "poa_funding.csv",
            "poa_ethics": "poa_ethics.csv"
        }

        for file_type, filename in list(file_types.items()):
            # Download
            s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
            bucket_name = self.settings.ejp_bucket
            storage = storage_context(self.settings)
            storage_provider = self.settings.storage_provider + "://"
            orig_resource = storage_provider + bucket_name + "/"
            try:
                storage_resource_origin = orig_resource + s3_key_name
            except TypeError:
                self.logger.info(
                    'PackagePoA unable to download CSV file for {file_type}'.format(
                        file_type=file_type
                    ))
                continue
            filename_plus_path = os.path.join(self.directories.get("CSV"), filename)
            with open(filename_plus_path, 'wb') as open_file:
                storage.get_resource_to_file(storage_resource_origin, open_file)
            # log last modified date if available
            s3_key = storage.get_resource_as_key(storage_resource_origin)
            self.logger.info('CSV file %s last_modified: %s' % (
                storage_resource_origin, getattr(s3_key, 'last_modified', '[unknown]')))

    def jatsgenerator_config(self, config_section):
        "parse the config values from the jatsgenerator config"
        return jats_conf.parse_raw_config(jats_conf.raw_config(
            config_section,
            self.settings.jatsgenerator_config_file))

    def generate_xml(self, article_id, pub_date=None, volume=None):
        """
        Given DOI number as article_id, use the POA library to generate
        article XML from the CSV files
        """
        # override the CSV directory in the ejp-csv-parser library
        jats_config = self.jatsgenerator_config(
            self.settings.jatsgenerator_config_section
        )
        parse.data.CSV_PATH = self.directories.get("CSV") + os.sep
        parse.data.TMP_DIR = self.directories.get("CSV_TMP")

        article = None
        try:
            article, self.error_count, self.error_messages = parse.build_article(
                article_id
            )
        except Exception as exception:
            self.logger.exception(
                "Exception in build_article for article_id %s: %s"
                % (article_id, str(exception))
            )
            raise

        # check for errors
        if self.error_count and self.error_count > 0:
            exception_message = (
                "Exception raised in generate_xml, error count: %s, error_messages: %s"
                % (self.error_count, ", ".join(self.error_messages))
            )
            self.logger.exception(exception_message)
            raise Exception(exception_message)

        if article:
            # Here can set the pub-date and volume, if provided
            if pub_date:
                pub_date_object = ArticleDate("pub", pub_date)
                article.add_date(pub_date_object)

            if volume:
                article.volume = volume

            # Override the output_dir in the jatsgenerator config
            jats_config['target_output_dir'] = self.directories.get("XML_OUTPUT")

            try:
                generate.build_xml_to_disk(
                    article_id, article, jats_config, True)
            except ExpatError as exception:
                self.logger.exception(
                    'Exception in build_xml_to_disk for article_id %s: %s' %
                    (article_id, str(exception)))
                raise

        # Copy to output_dir because we need it there
        xml_files = glob.glob(self.directories.get("XML_OUTPUT") + "/*.xml")
        for xml_file in xml_files:
            shutil.copy(xml_file, self.directories.get("OUTPUT"))

    def copy_files_to_s3_outbox(self):
        """
        Copy local files to the S3 bucket outbox
        """
        # TODO: log which files will be created
        pdf_files = glob.glob(self.directories.get("DECAPITATE_PDF") + "/*.pdf")
        for file_name_path in pdf_files:
            # Copy decap PDF to S3 outbox
            self.copy_file_to_bucket(file_name_path)

        xml_files = glob.glob(self.directories.get("XML_OUTPUT") + "/*.xml")
        for file_name_path in xml_files:
            # Copy XML file to S3 outbox
            self.copy_file_to_bucket(file_name_path)

        zip_files = glob.glob(self.directories.get("OUTPUT") + "/*.zip")
        for file_name_path in zip_files:
            # Copy supplements zip file to S3 outbox
            self.copy_file_to_bucket(file_name_path)

    def copy_file_to_bucket(self, file_name_path):
        """
        Given a boto bucket (already connected) and path to the file,
        copy the file to the publish_bucket using the same filename
        """
        # Get the file name from the full file path
        file_name = file_name_path.split(os.sep)[-1]

        # Create S3 object and save
        bucket_name = self.publish_bucket
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        s3_folder_name = self.outbox_folder
        resource_dest = storage_provider + bucket_name + "/" + s3_folder_name + file_name
        storage.set_resource_from_filename(resource_dest, file_name_path)
        self.logger.info("Copied %s to %s", file_name_path, resource_dest)

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
            self.settings.ses_poa_recipient_email)

        for email in recipient_email_list:
            # send the email by SMTP
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger)

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)
            self.logger.info('Email sending details: admin email, email %s, to %s' %
                             ("PackagePOA", email))

        return True

    def get_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = utils.get_activity_status_text(self.activity_status)

        subject = (
            self.name + " " + activity_status_text + " doi: " + str(self.doi) + ", " +
            datetime_string + ", eLife SWF domain: " + self.settings.domain
        )

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
        body += "document: " + str(self.document) + "\n"
        body += "doi: " + str(self.doi) + "\n"
        body += "\n"
        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "process_status: " + str(self.process_status) + "\n"
        body += "pdf_decap_status: " + str(self.pdf_decap_status) + "\n"
        body += "generate_xml_status: " + str(self.generate_xml_status) + "\n"

        if self.error_count and self.error_count > 0:
            body += "\n"
            body += "XML generation errors:" + "\n"
            body += "error_count: " + str(self.error_count) + "\n"
            body += "error_messages: " + ", ".join(self.error_messages) + "\n"

        body += "\n"
        body += "SWF workflow details: " + "\n"
        body += "activityId: " + str(self.get_activityId()) + "\n"
        body += "As part of workflowId: " + str(self.get_workflowId()) + "\n"
        body += "As at " + datetime_string + "\n"
        body += "Domain: " + self.settings.domain + "\n"

        body += "\n"

        body += "\n\nSincerely\n\neLife bot"

        return body


def get_doi_from_zip_file(filename=None):
    """
    Get the DOI from the zip file manifest.xml using the POA library
    Use the object variable as the default if not specified
    """
    if filename is None:
        return None
    # Good, continue
    try:
        with zipfile.ZipFile(filename, 'r') as current_zipfile:
            return transform.get_doi_from_zipfile(current_zipfile)
    except zipfile.BadZipfile:
        return None


def approve_for_packaging(doi_id):
    """
    After downloading the zip file but before starting to package it,
    do all the pre-packaging steps and checks, including to have a DOI
    """
    if doi_id is None:
        return False
    return True
