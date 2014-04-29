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
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib

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
        
        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)
        
        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "outbox/"
        self.published_folder = "published/"
        
        # Subfolders on the FTP site to deliver into
        self.ftp_subfolder_poa = "poa"
        self.ftp_subfolder_ds = "ds"
        
        # Track the success of some steps
        self.activity_status = None
        self.prepare_status = None
        self.approve_status = None
        self.ftp_status = None
        self.go_status = None
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
        
        # Prepare for HW
        self.prepare_status = self.prepare_for_hw()
        
        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()
        
        if self.approve_status is True:
            try:
                # Publish files
                self.ftp_files_to_endpoint(file_type = "/*_ds.zip", sub_dir = self.ftp_subfolder_ds)
                self.ftp_files_to_endpoint(file_type = "/*[0-9].zip", sub_dir = self.ftp_subfolder_poa)
                self.ftp_status = True
            except:
                self.ftp_status = False
                
            if self.ftp_status is True:
                try:
                    # Add go.xml files
                    self.create_go_xml_file("pap", self.ftp_subfolder_poa)
                    self.create_go_xml_file("ds", self.ftp_subfolder_ds)
                    self.ftp_go_xml_to_endpoint("pap", self.ftp_subfolder_poa)
                    self.ftp_go_xml_to_endpoint("ds", self.ftp_subfolder_ds)
                    self.go_status = True
                except:
                    self.go_status = False
            
            if self.ftp_status is True and self.go_status is True:
                # Clean up outbox
                print "Moving files from outbox folder to published folder"
                self.clean_outbox()
                self.outbox_status = True
                
            # Set the activity status of this activity based on successes
            if (self.prepare_status is True and
                self.ftp_status is True and
                self.go_status is True):
                # Published!
                self.publish_status = True
            else:
                self.publish_status = False
            
        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Send email
        self.add_email_to_queue()

        # Return the activity result, True or False
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
        try:
            self.elife_poa_lib.prepare.prepare_pdf_xml_for_ftp()
            return True
        except:
            return False

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
        From the made_ftp_ready_dir_name and self.published_folder
        return the S3 folder name to save published files into
        """
        to_folder = None
        
        made_ftp_ready_dir_name = self.get_made_ftp_ready_dir_name()
        if made_ftp_ready_dir_name:
            try:
                date_folder_name = made_ftp_ready_dir_name.split(os.sep)[-1]
                to_folder = self.published_folder + date_folder_name + "/"
            except:
                pass
        
        return to_folder
    
    def clean_outbox(self):
        """
        Clean out the S3 outbox folder
        """
        # Save the list of outbox contents to report on later
        outbox_s3_key_names = self.get_outbox_s3_key_names()
        
        if self.get_made_ftp_ready_dir_name():
            to_folder = self.get_to_folder_name()
            self.move_files_from_s3_folder_to_folder(self.outbox_folder, to_folder)

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
            email_type = "PublishPOA",
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
        
        # Count the files moved from the outbox, the files that were processed
        files_count = 0
        outbox_s3_key_names = self.get_outbox_s3_key_names()
        if outbox_s3_key_names:
            files_count = len(outbox_s3_key_names)
        
        subject = ( self.name + " " + activity_status_text +
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
        
        body += "prepare_status: " + str(self.prepare_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "ftp_status: " + str(self.ftp_status) + "\n"
        body += "go_status: " + str(self.go_status) + "\n"
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
        
        if self.outbox_status is True and files_count > 0:
            made_ftp_ready_dir_name = self.get_made_ftp_ready_dir_name()
            if made_ftp_ready_dir_name:
                to_folder = self.get_to_folder_name()
                body += "\n"
                body += "Files moved to: " + str(to_folder) + "\n"
        
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