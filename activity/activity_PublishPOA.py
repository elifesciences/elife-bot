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
        self.published_folder = "published/"
        
        # Subfolders on the FTP site to deliver into
        self.ftp_subfolder_poa = "poa"
        self.ftp_subfolder_ds = "ds"
        
        # Track the success of some steps
        self.publish_status = None
    
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
        
        # Approve files for publishing
        self.publish_status = self.approve_for_publishing()
        
        if self.publish_status is True:
            # Publish files
            self.ftp_files_to_endpoint(file_type = "/*_ds.zip", sub_dir = self.ftp_subfolder_ds)
            self.ftp_files_to_endpoint(file_type = "/*[0-9].zip", sub_dir = self.ftp_subfolder_poa)
            
            # Add go.xml files
            self.create_go_xml_file("pap", self.ftp_subfolder_poa)
            self.create_go_xml_file("ds", self.ftp_subfolder_ds)
            self.ftp_go_xml_to_endpoint("pap", self.ftp_subfolder_poa)
            self.ftp_go_xml_to_endpoint("ds", self.ftp_subfolder_ds)
        
            # Clean up outbox
            print "Moving files from outbox folder to published folder"
            self.clean_outbox()

        print str(self.publish_status)
        
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
        
    def get_made_ftp_ready_dir_name(self):
        """
        After running the prepare_for_hw, there should should be a subfolder in the
        MADE_FTP_READY directory, based on the run date. Return the name of it
        """
        numeric_folder_names = glob.glob(self.elife_poa_lib.settings.MADE_FTP_READY + "/[0-9]*")
        try:
            # There should be only one subdirectory with an all numeric name
            folder_name = numeric_folder_names[0]
        except:
            folder_name = None
        
        return folder_name

    def is_made_ftp_ready_dir_not_empty(self):
        """
        Lookup the numeric folder based on the date
        and check if it is empty
        """
        # Get the subfolder name for the made_ftp_ready_dir
        made_ftp_ready_dir_name = self.get_made_ftp_ready_dir_name()
        
        # Check for empty directory
        try:
            dir_list = os.listdir(made_ftp_ready_dir_name)
            if len(dir_list) > 0:
                return True
        except:
            return None
        
        return False

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the FTP endpoint
        Check for empty made_ftp_ready_dir
        Also, remove files that should not be uploaded due to incomplete
        sets of files per article
        """
        status = None
        # Get the subfolder name for the made_ftp_ready_dir
        made_ftp_ready_dir_name = self.get_made_ftp_ready_dir_name()
        
        # Check for empty directory
        if self.is_made_ftp_ready_dir_not_empty() is not True:
            status = False
        else:
            # Default until full sets of files checker is built
            status = True

        return status

    def ftp_files_to_endpoint(self, file_type, sub_dir = None):
        """
        Using the POA module, FTP files to endpoint
        as specified by the file_type to use in the glob
        e.g. "/*.zip"
        """
        zipfiles = glob.glob(self.elife_poa_lib.settings.FTP_TO_HW_DIR + file_type)
        self.elife_poa_lib.ftp.ftp_to_endpoint(zipfiles, sub_dir)
        
    def ftp_go_xml_to_endpoint(self, go_type, sub_dir):
        """
        Using the POA module, FTP the go.xml file
        """
        from_dir = self.get_go_xml_dir(sub_dir)
        go_xml_filename = from_dir + os.sep + "go.xml"
        
        zipfiles = []
        zipfiles.append(go_xml_filename)
        
        self.elife_poa_lib.ftp.ftp_to_endpoint(zipfiles, sub_dir)
        
    def get_go_xml_dir(self, sub_dir):
        """
        Given the sub_dir name, return the folder name
        based on the FTP_TO_HW_DIR directory. If the sub_dir
        does not exist, create it
        """
        from_dir = self.elife_poa_lib.settings.FTP_TO_HW_DIR + os.sep + sub_dir
        
        # Create the directory if not exists
        try:
            os.mkdir(from_dir)
        except OSError:
            pass
        
        return from_dir
        
    def create_go_xml_file(self, go_type, sub_dir):
        """
        Create a go.xml file of the particular type and save it
        to the particular sub directory
        """
        go_xml_content = ""
        if go_type == "pap":
            go_xml_content = self.get_go_xml_content(go_type)
        elif go_type == "ds":
            go_xml_content = self.get_go_xml_content(go_type)
        
        # Prepare folder to store it in
        from_dir = self.get_go_xml_dir(sub_dir)
        
        # Write to disk
        go_xml_filename = from_dir + os.sep + "go.xml"
        f = open(go_xml_filename, "w")
        f.write(go_xml_content)
        f.close()
        
    def get_go_xml_content(self, go_type):
        """
        Given the type of go.xml file, return the content for it
        """
        go_xml_content = ('<?xml version="1.0"?>'
            '<!DOCTYPE HWExpress PUBLIC "-//HIGHWIRE//DTD HighWire Express Marker DTD v1.1.2HW//EN"'
            ' "marker.dtd">')
        
        if go_type == "pap":
            go_xml_content += '<HWExpress type="pap">'
        elif go_type == "ds":
            go_xml_content += '<HWExpress type="ds">'
            
        go_xml_content += '  <site>elife</site>'
        go_xml_content += '</HWExpress>'
        
        return go_xml_content

    def move_files_from_s3_folder_to_folder(self, from_folder, to_folder):
        """
        Connect to the S3 bucket, and from the from_folder,
        move all the objects to the to_folder
        """
        
        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        s3_key_names = self.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = from_folder)
        
        for name in s3_key_names:
            # Download objects from S3 and save to disk

            filename = name.split("/")[-1]
            new_s3_key_name = to_folder + filename
            
            # First copy
            new_s3_key = None
            try:
                new_s3_key = bucket.copy_key(new_s3_key_name, bucket_name, name)
            except:
                pass
            
            # Then delete the old key if successful
            if(isinstance(new_s3_key, boto.s3.key.Key)):
                old_s3_key = bucket.get_key(name)
                old_s3_key.delete()
            
    def clean_outbox(self):
        """
        Clean out the S3 outbox folder
        """
        made_ftp_ready_dir_name = self.get_made_ftp_ready_dir_name()
        if made_ftp_ready_dir_name:
            date_folder_name = made_ftp_ready_dir_name.split(os.sep)[-1]
            to_folder = self.published_folder + date_folder_name + "/"
            self.move_files_from_s3_folder_to_folder(self.outbox_folder, to_folder)

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