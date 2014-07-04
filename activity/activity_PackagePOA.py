import os
import boto.swf
import json
import random
import datetime
import importlib
import calendar
import time

import zipfile
import requests
import urlparse
import glob
import shutil

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.ejp as ejplib
import provider.simpleDB as dblib

"""
PackagePOA activity
"""

class activity_PackagePOA(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PackagePOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Process POA zip file input, repackage, and save to S3."
        
        # Directory where POA library is stored
        self.poa_lib_dir_name = "elife-poa-xml-generation"
        
        # Where we specify the library to be imported
        self.elife_poa_lib = None
        
        # Import the libraries we will need
        self.import_imports()
        
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
        
        # Track the success of some steps
        self.activity_status = None
        self.approve_status = None
        self.process_status = None
        self.generate_xml_status = None
        self.pdf_decap_status = None
    
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 object
        self.document = data["data"]["document"]
        
        # Download POA zip file
        self.download_poa_zip(self.document)
        
        # Get the DOI from the zip file
        self.get_doi_from_zip_file()
        doi_id = self.get_doi_id_from_doi(self.doi)
        
        # Approve the DOI for packaging
        self.approve_status = self.approve_for_packaging(doi_id)
        
        if self.approve_status is False:
            # Bad. Fail the activity
            self.activity_status = False
            
        else:
            # Good, continue
            
            # Transform zip file
            self.process_status = self.process_poa_zipfile()
            self.pdf_decap_status = self.check_pdf_decap_failure()
            
            # Set the DOI and generate XML
            self.download_latest_csv()
            self.generate_xml_status = self.generate_xml(doi_id)
        
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
        return result

    def get_doi_id_from_doi(self, doi):
        """
        Extract just the integer doi_id value from the DOI string
        """
        try:
            doi_id = int(doi.split(".")[-1])
        except:
            doi_id = None
            
        return doi_id

    def download_poa_zip(self, document, bucket_name = None):
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
        filename_plus_path = self.elife_poa_lib.settings.EJP_INPUT_DIR + os.sep + document
        mode = "wb"
        f = open(filename_plus_path, mode)
        s3_key.get_contents_to_file(f)
        f.close()
        
        # Save the zip file name for later use
        self.poa_zip_filename = filename_plus_path
            
    def get_doi_from_zip_file(self, filename = None):
        """
        Get the DOI from the zip file manifest.xml using the POA library
        Use the object variable as the default if not specified
        """
        if filename is None:
            filename = self.poa_zip_filename
        if filename is None:
            return None
        
        # Good, continue
        current_zipfile = zipfile.ZipFile(filename, 'r')
        doi = self.elife_poa_lib.transform.get_doi_from_zipfile(current_zipfile)
        
        self.doi = doi
    
    def approve_for_packaging(self, doi_id):
        """
        After downloading the zip file but before starting to package it,
        do all the pre-packaging steps and checks, including to have a DOI
        """
        if doi_id is None:
            return False
        return True
    
    def process_poa_zipfile(self):
        """
        Using the POA transform-ejp-zip-to-hw-zip module
        """
        try:
            self.elife_poa_lib.transform.process_zipfile(
                zipfile_name = self.poa_zip_filename,
                output_dir   = self.elife_poa_lib.settings.STAGING_TO_HW_DIR
            )
            return True
        except:
            return False
        
    def check_pdf_decap_failure(self):
        """
        After processing the zipfile there should be a PDF present, as a
        result of decapitating the file. If not, return false
        """
        pdf_files = glob.glob(self.elife_poa_lib.settings.STAGING_DECAPITATE_PDF_DIR  + "/*.pdf")
        if len(pdf_files) <= 0:
            return False
        elif len(pdf_files) > 0:
            return True
        
    def download_latest_csv(self):
        """
        Download the latest CSV files from S3, rename them, and
        save to the XLS_PATH directory
        """
        
        # Key: File types, value: file to save as to disk
        file_types =    { "poa_author"             : "poa_author.csv",
                          "poa_license"            : "poa_license.csv",
                          "poa_manuscript"         : "poa_manuscript.csv",
                          "poa_received"           : "poa_received.csv",
                          "poa_subject_area"       : "poa_subject_area.csv",
                          "poa_research_organism"  : "poa_research_organism.csv",
                          "poa_abstract"           : "poa_abstract.csv",
                          "poa_title"              : "poa_title.csv"
                        }
        
        for file_type,filename in file_types.items():

            filename_plus_path = self.elife_poa_lib.settings.XLS_PATH + filename
            s3_key_name = self.ejp.find_latest_s3_file_name(file_type)
            
            # Download
            #print "downloading " + s3_key_name
            s3_key =  self.ejp.get_s3key(s3_key_name)
            contents = s3_key.get_contents_as_string()
            
            # Save to disk
            #print "saving to " + filename_plus_path
            mode = "w"
            f = open(filename_plus_path, mode)
            f.write(contents)
            f.close()

    def generate_xml(self, article_id):
        """
        Given DOI number as article_id, use the POA library to generate
        article XML from the CSV files
        """
        result = None
        try:
            result = self.elife_poa_lib.xml_generation.build_xml_for_article(article_id)
        except:
            result = False
        
        # Copy to STAGING_TO_HW_DIR because we need it there
        xml_files = glob.glob(self.elife_poa_lib.settings.TARGET_OUTPUT_DIR + "/*.xml")
        for f in xml_files:
            shutil.copy(f, self.elife_poa_lib.settings.STAGING_TO_HW_DIR)
            
        return result

    def copy_files_to_s3_outbox(self):
        """
        Copy local files to the S3 bucket outbox
        """

        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.publish_bucket)
        
        pdf_files = glob.glob(self.elife_poa_lib.settings.STAGING_DECAPITATE_PDF_DIR  + "/*.pdf")
        for absname in pdf_files:
            # Copy decap PDF to S3 outbox
            self.copy_file_to_bucket(bucket, absname)

        xml_files = glob.glob(self.elife_poa_lib.settings.TARGET_OUTPUT_DIR  + "/*.xml")
        for absname in xml_files:
            # Copy XML file to S3 outbox
            self.copy_file_to_bucket(bucket, absname)
            
        zip_files = glob.glob(self.elife_poa_lib.settings.FTP_TO_HW_DIR  + "/*.zip")
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
        if(type(self.settings.ses_poa_recipient_email) == list):
          for email in self.settings.ses_poa_recipient_email:
            recipient_email_list.append(email)
        else:
          recipient_email_list.append(self.settings.ses_poa_recipient_email)
    
        for email in recipient_email_list:
          # Add the email to the email queue
          self.db.elife_add_email_to_email_queue(
            recipient_email = email,
            sender_email = sender_email,
            email_type = "PackagePOA",
            format = "text",
            subject = subject,
            body = body)
          pass
        
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
      
        subject = ( self.name + " " + activity_status_text +
                    " doi: " + self.doi +
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
        body += "document: " + str(self.document) + "\n"
        body += "doi: " + str(self.doi) + "\n"
        body += "\n"
        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "process_status: " + str(self.process_status) + "\n"
        body += "pdf_decap_status: " + str(self.pdf_decap_status) + "\n"
        body += "generate_xml_status: " + str(self.generate_xml_status) + "\n"

        body += "\n"
        body += "SWF workflow details: " + "\n"
        body += "activityId: " + str(self.get_activityId()) + "\n"
        body += "As part of workflowId: " + str(self.get_workflowId()) + "\n"
        body += "As at " + datetime_string + "\n"
        body += "Domain: " + self.settings.domain + "\n"

        body += "\n"
        
        body += "\n\nSincerely\n\neLife bot"
        
        return body

    def import_imports(self):
        """
        Customised importing of the external library
        to override the settings
        MUST load settings module first, override the values
        BEFORE loading anything else, or the override will not take effect
        """
        
        # Load the files from parent directory - hellish imports but they
        #  seem to work now
        dir_name = self.poa_lib_dir_name
        
        self.import_poa_lib(dir_name)
        self.override_poa_settings(dir_name)
        self.import_poa_modules(dir_name)
    
    def import_poa_lib(self, dir_name):
        """
        POA lib import Step 1: import external library by directory name
        """
        self.elife_poa_lib = __import__(dir_name)
        self.reload_module(self.elife_poa_lib)
        
    def override_poa_settings(self, dir_name):
        """
        POA lib import Step 2: import settings modules then override
        """

        # Load external library settings
        self.elife_poa_lib.settings = importlib.import_module(dir_name + ".settings")
        # Reload the module fresh, so original directory names are reset
        self.reload_module(self.elife_poa_lib.settings)
        
        settings = self.elife_poa_lib.settings
        
        # Override the settings
        settings.XLS_PATH                   = self.get_tmp_dir() + os.sep + 'ejp-csv' + os.sep
        settings.TARGET_OUTPUT_DIR          = self.get_tmp_dir() + os.sep + settings.TARGET_OUTPUT_DIR
        settings.STAGING_TO_HW_DIR          = self.get_tmp_dir() + os.sep + settings.STAGING_TO_HW_DIR
        settings.FTP_TO_HW_DIR              = self.get_tmp_dir() + os.sep + settings.FTP_TO_HW_DIR
        settings.MADE_FTP_READY             = self.get_tmp_dir() + os.sep + settings.MADE_FTP_READY
        settings.EJP_INPUT_DIR              = self.get_tmp_dir() + os.sep + settings.EJP_INPUT_DIR
        settings.STAGING_DECAPITATE_PDF_DIR = self.get_tmp_dir() + os.sep + settings.STAGING_DECAPITATE_PDF_DIR
        settings.TMP_DIR                    = self.get_tmp_dir() + os.sep + settings.TMP_DIR

        settings.XLS_FILES = {  "authors"    : "poa_author.csv",
                                "license"    : "poa_license.csv",
                                "manuscript" : "poa_manuscript.csv",
                                "received"   : "poa_received.csv",
                                "subjects"   : "poa_subject_area.csv",
                                "organisms"  : "poa_research_organism.csv",
                                "abstract"   : "poa_abstract.csv",
                                "title"      : "poa_title.csv"}
        
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.xml = importlib.import_module(dir_name + ".xml_generation")
        self.reload_module(self.elife_poa_lib.xml)
        self.elife_poa_lib.transform = importlib.import_module(dir_name + ".transform-ejp-zip-to-hw-zip")
        self.reload_module(self.elife_poa_lib.transform)
    
    def reload_module(self, module):
        """
        Attempt to reload an imported module to reset it
        """
        try:
            reload(module)
        except:
            pass
    
    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.elife_poa_lib.settings.XLS_PATH)
        except:
            pass
        
        try:
            os.mkdir(self.elife_poa_lib.settings.TARGET_OUTPUT_DIR)
            os.mkdir(self.elife_poa_lib.settings.STAGING_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.FTP_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.MADE_FTP_READY)
            os.mkdir(self.elife_poa_lib.settings.EJP_INPUT_DIR)
            os.mkdir(self.elife_poa_lib.settings.STAGING_DECAPITATE_PDF_DIR)
            os.mkdir(self.elife_poa_lib.settings.TMP_DIR)
        except:
            pass