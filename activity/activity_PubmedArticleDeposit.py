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
import provider.article as articlelib
import provider.s3lib as s3lib

"""
PubmedArticleDeposit activity
"""

class activity_PubmedArticleDeposit(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PubmedArticleDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download article XML from pubmed outbox, generate pubmed article XML, and deposit with pubmed."
        
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
        
        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())
        
        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "pubmed/outbox/"
        self.published_folder = "pubmed/published/"
                
        # Track the success of some steps
        self.activity_status = None
        self.generate_status = None
        self.approve_status = None
        self.ftp_status = None
        self.outbox_status = None
        self.publish_status = None
                
        self.outbox_s3_key_names = None
        
        # Track XML files selected for pubmed XML
        self.xml_file_to_doi_map = {}
        self.article_published_file_names = []
        self.article_not_published_file_names = []
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 objects
        self.download_files_from_s3_outbox()
        
        # Generate pubmed XML 
        self.generate_status = self.generate_pubmed_xml()
        
        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()
        
        if self.approve_status is True:
            try:
                # Publish files
                self.ftp_files_to_endpoint(
                    from_dir = self.elife_poa_lib.settings.TMP_DIR,
                    file_type = "/*.xml",
                    sub_dir = "")
                self.ftp_status = True
            except:
                self.ftp_status = False
                       
            if self.ftp_status is True:
                # Clean up outbox
                print "Moving files from outbox folder to published folder"
                self.clean_outbox()
                self.upload_pubmed_xml_to_s3()
                self.outbox_status = True
                
            if self.ftp_status is True:
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
            self.add_email_to_queue()

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
        
        s3_key_names = s3lib.get_s3_key_names_from_bucket(
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
            
    def parse_article_xml(self, article_xml_files):
        """
        Given a list of article XML files, parse them into objects
        and save the file name for later use
        """
        
        # For each article XML file, parse it and save the filename for later
        articles = []
        for article_xml in article_xml_files:
            article_list = None
            article_xml_list = [article_xml]
            try:
                # Convert the XML files to article objects
                article_list = self.elife_poa_lib.parse.build_articles_from_article_xmls(article_xml_list)
            except:
                continue
            
            if len(article_list) > 0:
                article = article_list[0]
                articles.append(article)
                # Add article to the DOI to file name map
                self.xml_file_to_doi_map[article.doi] = article_xml
        
        return articles

    def generate_pubmed_xml(self):
        """
        Using the POA generatePubMedXml module
        """
        article_xml_files = glob.glob(self.elife_poa_lib.settings.STAGING_TO_HW_DIR + "/*.xml")
        
        articles = self.parse_article_xml(article_xml_files)

        # For each VoR article, set was_ever_poa property
        published_articles = []
        
        for article in articles:
            
            xml_file_name = self.xml_file_to_doi_map[article.doi]
            
            # Check if article was ever poa
            # Must be set to True or False to get it published
            if (article.is_poa() is False and
                self.article.check_was_ever_poa(article.doi) is True):
                article.was_ever_poa = True
            elif (article.is_poa() is False and
                self.article.check_was_ever_poa(article.doi) is False):
                article.was_ever_poa = False
                
            # Check if each article is published
            if self.article.check_is_article_published(
                doi = article.doi,
                is_poa = article.is_poa(),
                was_ever_poa = article.was_ever_poa) is True:
                
                # Add published article object to be processed
                published_articles.append(article)
                
                # Add filename to the list of published files
                self.article_published_file_names.append(xml_file_name)
            else:
                # Add the file to the list of not published articles, may be used later
                self.article_not_published_file_names.append(xml_file_name)
                
        # Will write the XML to the TMP_DIR
        if len(published_articles) > 0:
            try:
                self.elife_poa_lib.generate.build_pubmed_xml_for_articles(published_articles)
            except:
                return False
            
        return True

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the endpoint
        """
        status = None

        # Check for empty directory
        xml_files = glob.glob(self.elife_poa_lib.settings.TMP_DIR + "/*.xml")
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
    
    def ftp_files_to_endpoint(self, from_dir, file_type, sub_dir = None):
        """
        Using the POA module, FTP files to endpoint
        as specified by the file_type to use in the glob
        e.g. "/*.zip"
        """
        zipfiles = glob.glob(from_dir + file_type)
        self.elife_poa_lib.ftp.ftp_to_endpoint(zipfiles, sub_dir)

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
        
        s3_key_names = s3lib.get_s3_key_names_from_bucket(
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
        
        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        # Concatenate the expected S3 outbox file names
        s3_key_names = []
        for name in self.article_published_file_names:
            filename = name.split(os.sep)[-1]
            s3_key_name = self.outbox_folder + filename
            s3_key_names.append(s3_key_name)
        
        for name in s3_key_names:
            # Download objects from S3 and save to disk

            # Do not delete the from_folder itself, if it is in the list
            if name != self.outbox_folder:
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
        
    def upload_pubmed_xml_to_s3(self):
        """
        Upload a copy of the pubmed XML to S3 for reference
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
            email_type = "PubmedArticleDeposit",
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
        
        # Override the FTP settings with the bot environment settings
        settings.FTP_URI = self.settings.PUBMED_FTP_URI
        settings.FTP_USERNAME = self.settings.PUBMED_FTP_USERNAME
        settings.FTP_PASSWORD = self.settings.PUBMED_FTP_PASSWORD
        settings.FTP_CWD = self.settings.PUBMED_FTP_CWD
         
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.parse = importlib.import_module(dir_name + ".parsePoaXml")
        self.reload_module(self.elife_poa_lib.parse)
        self.elife_poa_lib.generate = importlib.import_module(dir_name + ".generatePubMedXml")
        self.reload_module(self.elife_poa_lib.generate)
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
            os.mkdir(self.elife_poa_lib.settings.STAGING_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.TMP_DIR)
        except:
            pass