import os
import boto.swf
import json
import random
import datetime
import importlib
import calendar
import time
import arrow

import zipfile
import requests
import urlparse
import glob
import shutil
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib

"""
DepositCrossref activity
"""

class activity_DepositCrossref(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "DepositCrossref"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download article XML from crossref outbox, generate crossref XML, and deposit with crossref."
        
        # Directory where POA library is stored
        self.poa_lib_dir_name = "elife-poa-xml-generation"
        
        # Where we specify the library to be imported
        self.elife_poa_lib = None
        
        # Import the libraries we will need
        self.import_imports()
        
        # Create output directories
        self.create_activity_directories()
        self.date_stamp = self.set_datestamp()
        
        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)
        
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
        
        self.outbox_s3_key_names = None
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
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
                self.deposit_files_to_endpoint(
                    file_type = "/*.xml",
                    sub_dir = self.elife_poa_lib.settings.TMP_DIR)
                self.publish_status = True
            except:
                self.publish_status = False
                            
            if self.publish_status is True:
                # Clean up outbox
                print "Moving files from outbox folder to published folder"
                self.clean_outbox()
                self.upload_crossref_xml_to_s3()
                self.outbox_status = True
                            
        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Return the activity result, True or False
        result = True

        return result

    def set_datestamp(self):
        a = arrow.utcnow()
        date_stamp = str(a.datetime.year) + str(a.datetime.month).zfill(2) + str(a.datetime.day).zfill(2)
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
        
        s3_key_names = self.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = self.outbox_folder,
            file_extensions = file_extensions)
        
        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            # Save .xml and .pdf to different folders
            if re.search(".*\\.xml$", name):
                dirname = self.elife_poa_lib.settings.STAGING_TO_HW_DIR

            filename_plus_path = dirname + os.sep + filename
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
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
        

    def generate_crossref_xml(self):
        """
        Using the POA generateCrossrefXml module
        """
        article_xml_files = glob.glob(self.elife_poa_lib.settings.STAGING_TO_HW_DIR + "/*.xml")
        try:
            # Will write the XML to the TMP_DIR
            self.elife_poa_lib.generate.build_crossref_xml_for_articles(article_xml_files)
            return True
        except:
            return False

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the endpoint
        """
        status = None

        # Check for empty directory
        article_xml_files = glob.glob(self.elife_poa_lib.settings.STAGING_TO_HW_DIR + "/*.xml")
        if len(article_xml_files) <= 0:
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
    
    def deposit_files_to_endpoint(self, file_type, sub_dir = None):
        """
        Using an HTTP POST, deposit the file to the endpoint
        """
        
        # TODO!!!!


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

            # Do not delete the from_folder itself, if it is in the list
            if name != from_folder:
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
    
    def get_outbox_s3_key_names(self, force = None):
        """
        Separately get a list of S3 key names form the outbox
        for reporting purposes, excluding the outbox folder itself
        """
        
        # Return cached values if available
        if self.outbox_s3_key_names and not force:
            return self.outbox_s3_key_names
        
        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        s3_key_names = self.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = self.outbox_folder)
        
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
        self.move_files_from_s3_folder_to_folder(self.outbox_folder, to_folder)
        
    def upload_crossref_xml_to_s3(self):
        """
        Upload a copy of the crossref XML to S3 for reference
        """
        xml_files = glob.glob(self.elife_poa_lib.settings.TMP_DIR + "/*.xml")

        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        date_folder_name = self.date_stamp
        s3_folder_name = self.published_folder + date_folder_name + "/" + "batch/"

        for xml_file in xml_files:
            s3key = boto.s3.key.Key(bucket)
            s3key.key = s3_folder_name + self.get_filename_from_path(xml_file, '.xml') + '.xml'
            s3key.set_contents_from_filename(xml_file, replace=True)

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
        settings.STAGING_TO_HW_DIR          = self.get_tmp_dir() + os.sep + settings.STAGING_TO_HW_DIR
        settings.TMP_DIR                    = self.get_tmp_dir() + os.sep + settings.TMP_DIR
         
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.generate = importlib.import_module(dir_name + ".generateCrossrefXml")
        self.reload_module(self.elife_poa_lib.generate)
        
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
            os.mkdir(self.elife_poa_lib.settings.STAGING_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.TMP_DIR)
        except:
            pass