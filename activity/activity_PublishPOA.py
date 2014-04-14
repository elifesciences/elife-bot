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
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

"""
PublishPOA activity
"""

class activity_PublishPOA(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PublishPOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download POA files in outbox, zip, and publish."
        
        # Directory where POA library is stored
        self.poa_lib_dir_name = "elife-poa-xml-generation"
        
        # Where we specify the library to be imported
        self.elife_poa_lib = None
        
        # Import the libraries we will need
        self.import_imports()
        
        # Create output directories
        self.create_activity_directories()
        
        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "outbox/"
    
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 objects
        self.download_files_from_s3_outbox()
        
        # Prepare for HW
        self.prepare_for_hw()
        
        # Publish files
        self.ftp_files_to_endpoint()
        
        # TODO!!! add go.xml file
        
        # TODO!!! Clean up outbox
        
        # TODO!  Assume all worked for now
        result = True

        return result

    def download_files_from_s3_outbox(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml and .pdf files to be bundled.
        """
        file_extensions = []
        file_extensions.append(".xml")
        file_extensions.append(".pdf")
        file_extensions.append(".zip")
        
        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        s3_key_names = self.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = self.outbox_folder,
            file_extensions = file_extensions)
        
        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            # Save .xml and .pdf to different folders
            if re.search(".*\\.pdf$", name):
                dirname = self.elife_poa_lib.settings.STAGING_TO_HW_DIR
                # Special on decap PDF file names, remove the _decap
                if re.search("decap\_", filename):
                    filename = filename.split("decap_")[-1]
            elif re.search(".*\\.xml$", name):
                dirname = self.elife_poa_lib.settings.STAGING_TO_HW_DIR
            elif re.search(".*\\.zip$", name):
                dirname = self.elife_poa_lib.settings.FTP_TO_HW_DIR

            contents = s3_key.get_contents_as_string()
            filename_plus_path = dirname + os.sep + filename
            mode = "wb"
            f = open(filename_plus_path, mode)
            f.write(contents)
            f.close()
        
    def get_s3_key_names_from_bucket(self, bucket, prefix = None, delimiter = '/', headers = None, file_extensions = None):
        """
        Given a connected boto bucket object, and optional parameters,
        from the prefix (folder name), get the s3 key names for
        non-folder objects, optionally that match a particular
        list of file extensions
        """
        s3_keys = []
        s3_key_names = []
        
        # Get a list of S3 objects
        bucketList = bucket.list(prefix = prefix, delimiter = delimiter, headers = headers)

        for item in bucketList:
          if(isinstance(item, boto.s3.key.Key)):
            # Can loop through each prefix and search for objects
            s3_keys.append(item)
        
        # Convert to key names instead of objects to make it testable later
        for key in s3_keys:
            s3_key_names.append(key.name)
        
        # Filter by file_extension
        if file_extensions is not None:
            s3_key_names = self.filter_list_by_file_extensions(s3_key_names, file_extensions)
            
        return s3_key_names
    
    def filter_list_by_file_extensions(self, s3_key_names, file_extensions):
        """
        Given a list of s3_key_names, and a list of file_extensions
        filter out all but the allowed file extensions
        Each file extension should start with a . dot
        """
        good_s3_key_names = []
        for name in s3_key_names:
            match = False
            for ext in file_extensions:
                # Match file extension as the end of the string and escape the dot
                pattern = ".*\\" + ext + "$"
                if(re.search(pattern, name) is not None):
                    match = True
            if match is True:
                good_s3_key_names.append(name)
        
        return good_s3_key_names
        

    def prepare_for_hw(self):
        """
        Using the POA prepare_xml_pdf_for_hw module
        """
        self.elife_poa_lib.prepare.prepare_pdf_xml_for_ftp()

    def ftp_files_to_endpoint(self):
        """
        Using the POA module, FTP files to endpoint
        """
        zipfiles = glob.glob(self.elife_poa_lib.settings.FTP_TO_HW_DIR + "/*.zip")
        self.elife_poa_lib.ftp.ftp_to_endpoint(zipfiles)

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
        importlib.import_module(dir_name + ".settings")
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
        
        # Override the FTP settings with the bot environment settings
        settings.FTP_URI = self.settings.POA_FTP_URI
        settings.FTP_USERNAME = self.settings.POA_FTP_USERNAME
        settings.FTP_PASSWORD = self.settings.POA_FTP_PASSWORD
        settings.FTP_CWD = self.settings.POA_FTP_CWD
         
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.prepare = importlib.import_module(dir_name + ".prepare_xml_pdf_for_hw")
        self.reload_module(self.elife_poa_lib.prepare)
        self.elife_poa_lib.ftp = importlib.import_module(dir_name + ".ftp_to_highwire")
        self.reload_module(self.elife_poa_lib.ftp)
        
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
        except:
            pass