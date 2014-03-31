import os
import boto.swf
import json
import random
import datetime
import importlib

import zipfile
import requests
import urlparse
import glob
import shutil

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.ejp as ejplib

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
        
        # Bucket for outgoing files
        self.publish_bucket = settings.bot_bucket
        self.outbox_folder = "poa/outbox/"
        
        # Some values to set later
        self.poa_zip_filename = None
        self.doi = None
    
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 object
        document = data["data"]["document"]
        
        # Download POA zip file
        self.download_poa_zip(document)
        
        # Get the DOI from the zip file
        self.get_doi_from_zip_file()
        
        # Transform zip file
        self.process_poa_zipfile()
        
        # Set the DOI and generate XML
        doi_id = self.get_doi_id_from_doi(self.doi)
        self.download_latest_csv()
        self.generate_xml(doi_id)
    
        # Copy finished files to S3 outbox
        self.copy_files_to_s3_outbox()
        
        # TODO!  Assume all worked for now
        result = True

        return result

    def get_doi_id_from_doi(self, doi):
        """
        Extract just the integer doi_id value from the DOI string
        """
        return int(doi.split(".")[-1])

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
        contents = s3_key.get_contents_as_string()
        filename_plus_path = self.elife_poa_lib.settings.EJP_INPUT_DIR + os.sep + document
        mode = "wb"
        f = open(filename_plus_path, mode)
        f.write(contents)
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
    
    def process_poa_zipfile(self):
        """
        Using the POA transform-ejp-zip-to-hw-zip module
        """
        self.elife_poa_lib.transform.process_zipfile(
            zipfile_name = self.poa_zip_filename,
            output_dir   = self.elife_poa_lib.settings.STAGING_TO_HW_DIR
        )
        
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
                          "poa_research_organism"  : "poa_research_organism.csv"
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
        result = self.elife_poa_lib.xml_generation.build_xml_for_article(article_id)
        
        # Copy to STAGING_TO_HW_DIR because we need it there
        xml_files = glob.glob(self.elife_poa_lib.settings.TARGET_OUTPUT_DIR + "/*.xml")
        for f in xml_files:
            shutil.copy(f, self.elife_poa_lib.settings.STAGING_TO_HW_DIR)

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
        
    def override_poa_settings(self, dir_name):
        """
        POA lib import Step 2: import settings modules then override
        """

        # Load external library settings
        importlib.import_module(dir_name + ".settings")
        
        settings = self.elife_poa_lib.settings
        
        # Override the settings
        settings.XLS_PATH                   = self.get_tmp_dir() + os.sep + 'ejp-csv' + os.sep
        settings.TARGET_OUTPUT_DIR          = self.get_tmp_dir() + os.sep + settings.TARGET_OUTPUT_DIR
        settings.STAGING_TO_HW_DIR          = self.get_tmp_dir() + os.sep + settings.STAGING_TO_HW_DIR
        settings.FTP_TO_HW_DIR              = self.get_tmp_dir() + os.sep + settings.FTP_TO_HW_DIR
        settings.MADE_FTP_READY             = self.get_tmp_dir() + os.sep + settings.MADE_FTP_READY
        settings.EJP_INPUT_DIR              = self.get_tmp_dir() + os.sep + settings.EJP_INPUT_DIR
        settings.STAGING_DECAPITATE_PDF_DIR = self.get_tmp_dir() + os.sep + settings.STAGING_DECAPITATE_PDF_DIR

        settings.XLS_FILES = {  "authors"    : "poa_author.csv",
                                "license"    : "poa_license.csv",
                                "manuscript" : "poa_manuscript.csv",
                                "received"   : "poa_received.csv",
                                "subjects"   : "poa_subject_area.csv",
                                "organisms"  : "poa_research_organism.csv"}
        
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        importlib.import_module(dir_name + ".xml_generation")
        self.elife_poa_lib.transform = importlib.import_module(dir_name + ".transform-ejp-zip-to-hw-zip")
        
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
        except:
            pass