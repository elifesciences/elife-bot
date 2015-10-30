import os
import boto.swf
import json
import random
import datetime
import importlib
import calendar
import time
import arrow

from collections import namedtuple

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
        
        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())
        
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
        
        # HTTP requests status
        self.http_request_status_code = []
        self.http_request_status_text = []
        
        self.outbox_s3_key_names = None
            
        # Track XML files selected for pubmed XML
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
        
        # Generate crossref XML
        self.generate_status = self.generate_crossref_xml()
        
        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()
        
        if self.approve_status is True:
            try:
                # Publish files
                self.publish_status = self.deposit_files_to_endpoint(
                    file_type = "/*.xml",
                    sub_dir = self.elife_poa_lib.settings.TMP_DIR)
            except:
                self.publish_status = False
                            
            if self.publish_status is True:
                # Clean up outbox
                print "Moving files from outbox folder to published folder"
                self.clean_outbox()
                self.upload_crossref_xml_to_s3()
                self.outbox_status = True
                            
        # Set the activity status of this activity based on successes
        if self.publish_status is not False and self.generate_status is not False:
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
            
            # Set the published date on v2, v3 etc. files
            if article_xml.find('v') > -1:
                article = None
                if len(article_list) > 0:
                    article = article_list[0]
                    
                pub_date_date = self.article.get_article_bucket_pub_date(article.doi, "poa")
                
                if article is not None and pub_date_date is not None:
                    # Emmulate the eLifeDate object use in the POA generation package
                    eLifeDate = namedtuple("eLifeDate", "date_type date")
                    pub_date = eLifeDate("pub", pub_date_date)
                    article.add_date(pub_date)
            
            if len(article_list) > 0:
                article = article_list[0]
                articles.append(article)
            
        return articles

    def generate_crossref_xml(self):
        """
        Using the POA generateCrossrefXml module
        """
        article_xml_files = glob.glob(self.elife_poa_lib.settings.STAGING_TO_HW_DIR + "/*.xml")
        
        for xml_file in article_xml_files:
            generate_status = True
            
            # Convert the single value to a list for processing
            xml_files = [xml_file]
            article_list = self.parse_article_xml(xml_files)
            
            if len(article_list) == 0:
                self.article_not_published_file_names.append(xml_file)
                continue
            else:
                article = article_list[0]
            
            if self.approve_to_generate(article) is not True:
                generate_status = False
            else:
                try:
                    # Will write the XML to the TMP_DIR
                    self.elife_poa_lib.generate.build_crossref_xml_for_articles(article_list)
                except:

                    generate_status = False
                
            if generate_status is True:
                # Add filename to the list of published files
                self.article_published_file_names.append(xml_file)
            else:
                # Add the file to the list of not published articles, may be used later
                self.article_not_published_file_names.append(xml_file)
        
        # Any files generated is a sucess, even if one failed
        return True

    def approve_to_generate(self, article):
        """
        Given an article object, decide if crossref deposit should be
        generated from it
        """
        approved = None
        # Embargo if the pub date is in the future
        if article.get_date('pub'):
            pub_date = article.get_date('pub').date
            now_date = time.gmtime()
            if pub_date < now_date:
                approved = True
            else:
                # Pub date is later than now, do not approve
                approved = False
        else:
            # No pub date, then we approve it
            approved = True
            
        return approved
    

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
        
        # Default return status
        status = True
        
        url = self.settings.crossref_url
        payload = {'operation':    'doMDUpload',
                   'login_id':     self.settings.crossref_login_id,
                   'login_passwd': self.settings.crossref_login_passwd
                   }
        
        # Crossref XML, should be only one but check for multiple
        xml_files = glob.glob(sub_dir + file_type)
        
        for xml_file in xml_files:
            files = {'file': open(xml_file, 'rb')}
            
            r = requests.post(url, data=payload, files=files)
 
            # Check for good HTTP status code
            if r.status_code != requests.codes.ok:
                status = False
            #print r.text
            self.http_request_status_text.append("XML file: " + xml_file)
            self.http_request_status_text.append("HTTP status: " + str(r.status_code))
            self.http_request_status_text.append("HTTP response: " + r.text)
            
        return status

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
            email_type = "DepositCrossref",
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
            body += "Published files generated crossref XML: " + "\n"
            for name in self.article_published_file_names:
                body += name.split(os.sep)[-1] + "\n"

        # Report on not published files
        if len(self.article_not_published_file_names) > 0:
            body += "\n"
            body += "Files not approved or failed crossref XML: " + "\n"
            for name in self.article_not_published_file_names:
                body += name.split(os.sep)[-1] + "\n"
            
        body += "\n"
        body += "-------------------------------\n"
        body += "HTTP deposit details: " + "\n"
        for code in self.http_request_status_code:
            body += "Status code: " + str(code) + "\n"
        for text in self.http_request_status_text:
            body += str(text) + "\n"
            
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
         
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.parse = importlib.import_module(dir_name + ".parsePoaXml")
        self.reload_module(self.elife_poa_lib.parse)
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