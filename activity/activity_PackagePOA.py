import os
import boto.swf
import json
import time
import zipfile

import glob
import shutil

import activity

import boto.s3
from boto.s3.connection import S3Connection

from jatsgenerator import generate
from jatsgenerator import conf as jats_conf
from packagepoa import transform
from packagepoa import conf as poa_conf
from elifearticle.article import ArticleDate

import provider.ejp as ejplib
import provider.simpleDB as dblib
import provider.lax_provider as lax_provider
from provider import utils

"""
PackagePOA activity
"""

class activity_PackagePOA(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PackagePOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = "Process POA zip file input, repackage, and save to S3."

        # Activity directories
        self.EJP_INPUT_DIR = os.path.join(self.get_tmp_dir(), 'ejp_input')
        self.XML_OUTPUT_DIR = os.path.join(self.get_tmp_dir(), 'generated_xml_output')
        self.CSV_DIR = os.path.join(self.get_tmp_dir(), 'csv_data')
        self.DECAPITATE_PDF_DIR = os.path.join(self.get_tmp_dir(), 'decapitate_pdf_dir')
        self.TMP_DIR = os.path.join(self.get_tmp_dir(), 'tmp')
        self.OUTPUT_DIR = os.path.join(self.get_tmp_dir(), 'output_dir')

        # Create output directories
        self.create_activity_directories()

        # Create an EJP provider to access S3 bucket holding CSV files
        self.ejp = ejplib.EJP(settings, self.get_tmp_dir())

        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)

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
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Download the S3 object
        self.document = data["data"]["document"]

        # Download POA zip file
        self.poa_zip_filename = self.download_poa_zip(self.document)

        # Get the DOI from the zip file
        self.doi = self.get_doi_from_zip_file(self.poa_zip_filename)
        doi_id = utils.msid_from_doi(self.doi)

        # Approve the DOI for packaging
        self.approve_status = self.approve_for_packaging(doi_id)

        if self.approve_status is False:
            # Bad. Fail the activity
            self.activity_status = False

        else:
            # Good, continue

            # Transform zip file
            self.process_status = self.process_poa_zipfile(self.poa_zip_filename)
            self.pdf_decap_status = self.check_pdf_decap_failure()

            # Set the DOI and generate XML
            self.download_latest_csv()
            pub_date = self.get_pub_date(doi_id)
            volume = utils.volume_from_pub_date(pub_date)
            self.generate_xml_status = self.generate_xml(doi_id, pub_date, volume)

            # Copy finished files to S3 outbox
            self.copy_files_to_s3_outbox()

            # Set the activity status of this activity based on successes
            if (self.process_status is True and
                    self.pdf_decap_status is True and
                    self.generate_xml_status is True):
                self.activity_status = True
            else:
                self.activity_status = False

        # Send email
        self.add_email_to_queue()

        # Return the activity result, True or False
        result = True

        if self.activity_status is True:
            self.clean_tmp_dir()

        return result

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

    def download_poa_zip(self, document, bucket_name=None):
        """
        Given the s3 object name as document, download it from the
        POA delivery bucket and save file to disk in the EJP_INPUT_DIR
        """
        if bucket_name is None:
            # Default bucket
            bucket_name = self.settings.poa_bucket

        #print bucket_name
        #print document

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        # Get the S3 object key
        s3_key = bucket.get_key(document)

        # Download and save to disk
        filename_plus_path = self.EJP_INPUT_DIR + os.sep + document
        mode = "wb"
        f = open(filename_plus_path, mode)
        s3_key.get_contents_to_file(f)
        f.close()

        return filename_plus_path

    def packagepoa_config(self, config_section):
        "parse the config values from the jatsgenerator config"
        return poa_conf.parse_raw_config(poa_conf.raw_config(
            config_section,
            self.settings.packagepoa_config_file))

    def get_doi_from_zip_file(self, filename=None):
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
        except:
            return None

    def approve_for_packaging(self, doi_id):
        """
        After downloading the zip file but before starting to package it,
        do all the pre-packaging steps and checks, including to have a DOI
        """
        if doi_id is None:
            return False
        return True

    def process_poa_zipfile(self, poa_zip_filename):
        """
        Using the POA transform-ejp-zip-to-hw-zip module
        """
        poa_config = self.packagepoa_config(self.settings.packagepoa_config_section)
        # override the output directories
        poa_config['output_dir'] = self.OUTPUT_DIR
        poa_config['decapitate_pdf_dir'] = self.DECAPITATE_PDF_DIR
        poa_config['tmp_dir'] = self.TMP_DIR
        try:
            transform.process_zipfile(
                zipfile_name=poa_zip_filename,
                poa_config=poa_config
            )
            return True
        except:
            return False

    def check_pdf_decap_failure(self):
        """
        After processing the zipfile there should be a PDF present, as a
        result of decapitating the file. If not, return false
        """
        pdf_files = glob.glob(self.DECAPITATE_PDF_DIR  + "/*.pdf")
        if len(pdf_files) <= 0:
            return False
        elif len(pdf_files) > 0:
            return True

    def download_latest_csv(self):
        """
        Download the latest CSV files from S3, rename them, and
        save to the CSV_DIR directory
        """

        # Key: File types, value: file to save as to disk
        file_types = {
            "poa_author"             : "poa_author.csv",
            "poa_license"            : "poa_license.csv",
            "poa_manuscript"         : "poa_manuscript.csv",
            "poa_received"           : "poa_received.csv",
            "poa_subject_area"       : "poa_subject_area.csv",
            "poa_research_organism"  : "poa_research_organism.csv",
            "poa_abstract"           : "poa_abstract.csv",
            "poa_title"              : "poa_title.csv",
            "poa_keywords"           : "poa_keywords.csv",
            "poa_group_authors"      : "poa_group_authors.csv",
            "poa_datasets"           : "poa_datasets.csv",
            "poa_funding"            : "poa_funding.csv",
            "poa_ethics"             : "poa_ethics.csv"
        }

        for file_type, filename in file_types.items():

            filename_plus_path = self.CSV_DIR + os.sep + filename
            s3_key_name = self.ejp.find_latest_s3_file_name(file_type)

            # Download
            #print "downloading " + s3_key_name
            s3_key = self.ejp.get_s3key(s3_key_name)
            contents = s3_key.get_contents_as_string()

            # Save to disk
            #print "saving to " + filename_plus_path
            mode = "w"
            f = open(filename_plus_path, mode)
            f.write(contents)
            f.close()

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
        result = None
        # override the CSV directory in the ejp-csv-parser library
        generate.data.CSV_PATH = self.CSV_DIR + os.sep
        jats_config = self.jatsgenerator_config(self.settings.jatsgenerator_config_section)
        article = generate.build_article_from_csv(article_id, jats_config)

        if article:
            # Here can set the pub-date and volume, if provided
            if pub_date:
                pub_date_object = ArticleDate("pub", pub_date)
                article.add_date(pub_date_object)
    
            if volume:
                article.volume = volume

            # Override the output_dir in the jatsgenerator config
            jats_config['target_output_dir'] = self.XML_OUTPUT_DIR
            result = generate.build_xml_to_disk(
                article_id, article, jats_config, True)
        else:
            result = False

        # Copy to OUTPUT_DIR because we need it there
        xml_files = glob.glob(self.XML_OUTPUT_DIR + "/*.xml")
        for f in xml_files:
            shutil.copy(f, self.OUTPUT_DIR)

        return result

    def copy_files_to_s3_outbox(self):
        """
        Copy local files to the S3 bucket outbox
        """

        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.publish_bucket)

        pdf_files = glob.glob(self.DECAPITATE_PDF_DIR  + "/*.pdf")
        for absname in pdf_files:
            # Copy decap PDF to S3 outbox
            self.copy_file_to_bucket(bucket, absname)

        xml_files = glob.glob(self.XML_OUTPUT_DIR  + "/*.xml")
        for absname in xml_files:
            # Copy XML file to S3 outbox
            self.copy_file_to_bucket(bucket, absname)

        zip_files = glob.glob(self.OUTPUT_DIR  + "/*.zip")
        for absname in zip_files:
            # Copy supplements zip file to S3 outbox
            self.copy_file_to_bucket(bucket, absname)

    def copy_file_to_bucket(self, bucket, absname):
        """
        Given a boto bucket (already connected) and path to the file,
        copy the file to the publish_bucket using the same filename
        """
        # Get the file name from the full file path
        arcname = absname.split(os.sep)[-1]
        s3_key_name = self.outbox_folder + arcname
        # Create S3 object and save
        s3key = boto.s3.key.Key(bucket)
        s3key.key = s3_key_name
        s3key.set_contents_from_filename(absname, replace=True)

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
        if type(self.settings.ses_poa_recipient_email) == list:
            for email in self.settings.ses_poa_recipient_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_poa_recipient_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            self.db.elife_add_email_to_email_queue(
                recipient_email=email,
                sender_email=sender_email,
                email_type="PackagePOA",
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

        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

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

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [
                self.XML_OUTPUT_DIR,
                self.CSV_DIR,
                self.EJP_INPUT_DIR,
                self.DECAPITATE_PDF_DIR,
                self.TMP_DIR,
                self.OUTPUT_DIR
            ]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
