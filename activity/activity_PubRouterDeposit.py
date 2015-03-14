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
PubRouterDeposit activity
"""

class activity_PubRouterDeposit(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PubRouterDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = ("Download article XML from pub_router outbox, \
                            approve each for publication, and deposit files via FTP to pub router.")
        
        # Create output directories
        self.date_stamp = self.set_datestamp()
        
        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)
        
        # Instantiate a new article object to provide some helper functions
        self.article = articlelib.article(self.settings, self.get_tmp_dir())
        
        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "pub_router/outbox/"
        self.published_folder = "pub_router/published/"
        
        # Track the success of some steps
        self.activity_status = None
        self.ftp_status = None
        self.outbox_status = None
        self.publish_status = None
        
        self.outbox_s3_key_names = None
        
        # Type of FTPArticle workflow to start
        self.workflow = "HEFCE"
        
        # Track XML files selected
        self.article_xml_filenames = []
        self.xml_file_to_doi_map = {}
        self.articles = []

        #self.article_published_file_names = []
        #self.article_not_published_file_names = []
        
        self.admin_email_content = ''
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 objects from the outbox
        self.article_xml_filenames = self.download_files_from_s3_outbox()
        # Parse the XML
        self.articles = self.parse_article_xml(self.article_xml_filenames)
        # Approve the articles to be sent
        self.articles_approved = self.approve_articles(self.articles)
      
      
        for article in self.articles_approved:
            # Start a workflow for each article this is approved to publish
            print article.doi
            # Second test, start a ping workflow from an activity
            workflow_id = "ping_" + "FTPArticle_" + self.workflow + "_" + str(article.doi_id)
            workflow_name = "Ping"
            workflow_version = "1"
            child_policy = None
            execution_start_to_close_timeout = None
            data = {}
            data['workflow'] = self.workflow
            data['elife_id'] = article.doi_id
            
            input_json = {}
            input_json['data'] = data
            
            input = json.dumps(input_json)
            conn = boto.swf.layer1.Layer1(self.settings.aws_access_key_id,
                                          self.settings.aws_secret_access_key)
            try:
                response = conn.start_workflow_execution(self.settings.domain, workflow_id,
                                                         workflow_name, workflow_version,
                                                         self.settings.default_task_list,
                                                         child_policy,
                                                         execution_start_to_close_timeout, input)
            except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                # There is already a running workflow with that ID, cannot start another
                message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
                print message
                if(self.logger):
                    self.logger.info(message)
            

        # Clean up outbox
        print "Moving files from outbox folder to published folder"
        self.clean_outbox()
        self.outbox_status = True
        
        # Send email to admins with the status
        self.activity_status = True
        self.send_admin_email()

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
        download the .xml to be processed
        """
        filenames = []
        
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
            
            # Download to the activity temp directory
            dirname = self.get_tmp_dir()
  
            filename_plus_path = dirname + os.sep + filename
            
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()
            
            filenames.append(filename_plus_path)
            
        return filenames
            
    def parse_article_xml(self, article_xml_filenames):
      """
      Given a list of article XML filenames,
      parse the files and add the article object to our article map
      """
      
      articles = []
      
      for article_xml_filename in article_xml_filenames:
    
        article = self.create_article()
        article.parse_article_file(article_xml_filename)
        if(self.logger):
          log_info = "Parsed " + article.doi_url
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
        # Add article object to the object list
        articles.append(article)
  
        # Add article to the DOI to file name map
        self.xml_file_to_doi_map[article.doi] = article_xml_filename
      
      return articles

    def create_article(self, doi_id = None):
      """
      Instantiate an article object and optionally populate it with
      data for the doi_id (int) supplied
      """
      
      # Instantiate a new article object
      article = articlelib.article(self.settings, self.get_tmp_dir())
      
      if doi_id:
        # Get and parse the article XML for data
        # Convert the doi_id to 5 digit string in case it was an integer
        if type(doi_id) == int:
          doi_id = str(doi_id).zfill(5)
        article_xml_filename = article.download_article_xml_from_s3(doi_id)
        article.parse_article_file(self.get_tmp_dir() + os.sep + article_xml_filename)
      return article

    def approve_articles(self, articles):
      """
      Given a list of article objects, approve them for processing    
      """
      
      approved_articles = []
          
      # Keep track of which articles to remove at the end
      remove_article_doi = []
      
      # Create a blank article object to use its functions
      blank_article = self.create_article()
      # Remove based on published status
      
      for article in articles:
        # Article object knows if it is POA or not
        is_poa = article.is_poa
        # Need to check S3 for whether the DOI was ever POA
        #  using the blank article object to hopefully make only one S3 connection
        was_ever_poa = blank_article.check_was_ever_poa(article.doi)
        
        # Set the value on the article object for later, it is useful
        article.was_ever_poa = was_ever_poa
        
        # Now can check if published
        is_published = blank_article.check_is_article_published(article.doi, is_poa, was_ever_poa)
        if is_published is not True:
          if(self.logger):
            log_info = "Removing because it is not published " + article.doi
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
          remove_article_doi.append(article.doi)
      
      # Check if article is a resupply
      # TODO !!!

      # Check if article is on the blacklist to not send again
      # TODO !!!
      
      # Can remove the articles now without affecting the loops using del
      for article in articles:
        if article.doi not in remove_article_doi:
          approved_articles.append(article)
  
      return approved_articles
    
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
      
      to_folder = self.get_to_folder_name()
      
      # Move only the published files from the S3 outbox to the published folder
      bucket_name = self.publish_bucket
      
      # Connect to S3 and bucket
      s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
      bucket = s3_conn.lookup(bucket_name)
      
      # Concatenate the expected S3 outbox file names
      s3_key_names = []
      
      # Compile a list of the published file names
      remove_doi_list = []
      processed_file_names = []
      for article in self.articles_approved:
        remove_doi_list.append(article.doi)
          
      for k, v in self.xml_file_to_doi_map.items():
        if k in remove_doi_list:
          processed_file_names.append(v)
      
      for name in processed_file_names:
          filename = name.split(os.sep)[-1]
          s3_key_name = self.outbox_folder + filename
          s3_key_names.append(s3_key_name)
      print json.dumps(s3_key_names)
      
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
        
    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """
        # Connect to DB
        db_conn = self.db.connect()
        
        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)
      
        current_time = time.gmtime()
        
        body = self.get_admin_email_body(current_time)
        subject = self.get_admin_email_subject(current_time)
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
            email_type = "PublicationEmail",
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
      
    def get_admin_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)
        
        activity_status_text = self.get_activity_status_text(self.activity_status)
        
        subject = ( self.name + " " + activity_status_text +
                    ", " + datetime_string +
                    ", eLife SWF domain: " + self.settings.domain)
        
        return subject
  
    def get_admin_email_body(self, current_time):
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
        body += "Details:" + "\n"
        body += "\n"
        body += self.admin_email_content + "\n"
        body += "\n"
              
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


