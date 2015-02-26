import boto.swf
import json
import random
import datetime
import calendar
import time
import os

from collections import namedtuple

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib
import provider.templates as templatelib
import provider.ejp as ejplib
import provider.article as articlelib
import provider.s3lib as s3lib

"""
PublicationEmail activity
"""

class activity_PublicationEmail(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "PublicationEmail"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Queue emails to notify of a new article publication."
    
    # Data provider
    self.db = dblib.SimpleDB(settings)
    
    # Templates provider
    self.templates = templatelib.Templates(settings, self.get_tmp_dir())

    # EJP data provider
    self.ejp = ejplib.EJP(settings, self.get_tmp_dir())
    
    # Bucket for outgoing files
    self.publish_bucket = settings.poa_packaging_bucket
    self.outbox_folder = "publication_email/outbox/"
    self.published_folder = "publication_email/published/"
    
    # Track XML files selected for publication
    self.article_xml_filenames = []
    self.xml_file_to_doi_map = {}
    self.articles = []
    self.related_articles = []
    self.articles_approved = []
    
    # Default is do not send duplicate emails
    self.allow_duplicates = False
    
    # Article types for which not to send emails
    self.article_types_do_not_send = []
    self.article_types_do_not_send.append('editorial')
    self.article_types_do_not_send.append('correction')
    self.article_types_do_not_send.append('discussion')
    # Email types, for sending previews of each template
    self.email_types = []
    self.email_types.append('author_publication_email_POA')
    self.email_types.append('author_publication_email_VOR_after_POA')
    self.email_types.append('author_publication_email_VOR_no_POA')
    self.email_types.append('author_publication_email_Insight_to_VOR')
    
  def do_activity(self, data = None):
    """
    PublicationEmail activity, do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    # Connect to DB
    db_conn = self.db.connect()
    
    # Check for whether the workflow execution was told to allow duplicate emails
    #  default is False
    try:
      self.allow_duplicates = data["data"]["allow_duplicates"]
    except KeyError:
      # Not specified? Ok, just use the default
      pass
    
    # Download templates
    templates_downloaded = self.download_templates()
    if templates_downloaded is True:
      
      # Download the article XML from S3 and parse them
      self.article_xml_filenames = self.download_files_from_s3_outbox()
      self.articles = self.parse_article_xml(self.article_xml_filenames)
      
      self.articles_approved = self.approve_articles(self.articles)
      
      if(self.logger):
        self.logger.info("Total parsed articles: " + str(len(self.articles)))
        self.logger.info("Total approved articles " + str(len(self.articles_approved)))
      
      for article in self.articles_approved:
        
        # Ready to format emails and queue them
        
        # First send author emails
        authors = self.get_authors(article.doi_id)

        # TODO!! Determine which email type to send
        #email_type = "author_publication_email_VOR_no_POA"
    
        # Temporary for testing, send a test run
        #self.send_email_testrun(self.email_types, article.doi_id, authors, article)
      
    return True
  
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
        self.logger.info("Parsed " + article.doi_url)
      # Add article object to the object list
      articles.append(article)

      # Add article to the DOI to file name map
      self.xml_file_to_doi_map[article.doi] = article_xml_filename
    
    return articles

  def download_templates(self):
    """
    Download the email templates from s3    
    """
    
    # Prepare email templates
    self.templates.download_email_templates_from_s3()
    if(self.templates.email_templates_warmed is not True):
      if(self.logger):
        self.logger.info('PublicationEmail email templates did not warm successfully')
      # Stop now! Return False if we do not have the necessary files
      return False
    else:
      if(self.logger):
        self.logger.info('PublicationEmail email templates warmed')
      return True

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
  
  def get_related_article(self, doi):
    """
    When populating related articles, given a DOI,
    download the article XML and parse it,
    return a previously parsed article object if it exists
    """
    
    article = None
    
    for article in self.related_articles:
      if article.doi_url == doi:
        # Return an existing article object
        if(self.logger):
          self.logger.info("Hit the article cache on " + doi)
        return article
    
    # Article for this DOI does not exist, populate it
    doi_id = int(doi.split(".")[-1])
    article = self.create_article(doi_id)
    
    self.related_articles.append(article)
    
    if(self.logger):
      self.logger.info("Building article for " + doi)

    return article
  
  def approve_articles(self, articles):
    """
    Given a list of article objects, approve them for processing    
    """
    
    approved_articles = []
    
    # Approach this by adding all the articles at first, then remove the unwanted ones
    approved_articles = list(articles)
    
    # Remove based on article type
    for i, article in enumerate(approved_articles):
      if article.article_type in self.article_types_do_not_send:
        if(self.logger):
          self.logger.info("Removing based on article type " + article.doi)
        del approved_articles[i]
        

    # Create a blank article object to use its functions
    blank_article = self.create_article()
    # Remove based on published status
    for i, article in enumerate(approved_articles):

      # Article object knows if it is POA or not
      is_poa = article.is_poa()
      # Need to check S3 for whether the DOI was ever POA
      #  using the blank article object to hopefully make only one S3 connection
      was_ever_poa = blank_article.check_was_ever_poa(article.doi)
      
      # Now can check if published
      is_published = blank_article.check_is_article_published(article.doi, is_poa, was_ever_poa)
      if is_published is not True:
        if(self.logger):
          self.logger.info("Removing because it is not published " + article.doi)
        del approved_articles[i]
    
    return approved_articles
    
  
  def send_email_testrun(self, email_types, elife_id, authors, article):
    """
    For testing the workflow and the templates
    Given an article (and its elife_id), list of email types and
    list of authors, it will send lots of emails
    and also bypass the default allow_duplicates value
    Should only be run on the dev environment which should not have live email addresses on it
    """
    
    # Failsafe check, do not continue if we think we are not on the dev environment
    # Expecting    self.settings.bucket = 'elife-articles-dev'  look for the dev at the end
    if self.settings.bucket.split('-')[-1] != 'dev':
      return
    
    # Allow duplicates, will send
    self.allow_duplicates = True
    
    # Send an email to each author
    for author in authors:
      # Test sending each type of template
      for email_type in self.email_types:
        self.send_email(email_type, elife_id, author, article)
      
      # For testing set the article as its own related article then send again
      
      # Look for a related article, if not found, set the article to be related to itself
      related_article_doi = article.get_article_related_insight_doi()
      if related_article_doi is None:
        related_article_doi = article.doi_url
        
      related_article = self.get_related_article(related_article_doi)
      article.set_related_insight_article(related_article)
      for email_type in ['author_publication_email_VOR_no_POA',
                         'author_publication_email_VOR_after_POA']:
        self.send_email(email_type, elife_id, author, article)
    
  
  def send_email(self, email_type, elife_id, author, article):
    """
    Given the email type and author,
    decide whether to send the email (after checking for duplicates)
    and queue the email
    """
    
    # First process the headers
    headers = self.templates.get_email_headers(
      email_type = email_type,
      author = author,
      article = article,
      format = "html")
    
    # Get the article published date timestamp
    pub_date_timestamp = None
    date_scheduled_timestamp = 0
    try:
      pub_date_timestamp = article.pub_date_timestamp
      date_scheduled_timestamp = pub_date_timestamp
    except:
      pass
    
    # Duplicate email check, can bypass with allow_duplicates = True
    if(self.allow_duplicates is True):
      duplicate = False
    else:
      duplicate = self.is_duplicate_email(
        doi_id          = elife_id,
        email_type      = headers["email_type"],
        recipient_email = author.e_mail)
    
    if(duplicate is True):
      if(self.logger):
        self.logger.info('Duplicate email: doi_id: %s email_type: %s recipient_email: %s' % (elife_id, headers["email_type"], author.e_mail))
        
    elif(duplicate is False):
      # Queue the email
      self.queue_author_email(
        email_type = email_type,
        author  = author,
        headers = headers,
        article = article,
        doi_id  = elife_id,
        date_scheduled_timestamp = date_scheduled_timestamp,
        format  = "html")
    
  
  def queue_author_email(self, email_type, author, headers, article, doi_id, date_scheduled_timestamp, format = "html"):
    """
    Format the email body and add it to the live queue
    Only call this to send actual emails!
    """
    body = self.templates.get_email_body(
      email_type = email_type,
      author  = author,
      article = article,
      format  = format)

    # Add the email to the email queue
    self.db.elife_add_email_to_email_queue(
      recipient_email = author.e_mail,
      sender_email    = headers["sender_email"],
      email_type      = headers["email_type"],
      format          = headers["format"],
      subject         = headers["subject"],
      body            = body,
      doi_id          = doi_id,
      date_scheduled_timestamp = date_scheduled_timestamp)
    
  def is_duplicate_email(self, doi_id, email_type, recipient_email):
    """
    Use the SimpleDB provider to count the number of emails
    in the queue for the particular combination of variables
    to determine whether we should not send an email twice
    Default: return None
      No matching emails: return False
      Is a matching email in the queue: return True
    """
    duplicate = None
    try:
      count = 0
      
      # Count all emails of all sent statuses
      for sent_status in True,False,None:
        result_list = self.db.elife_get_email_queue_items(
          query_type = "count",
          doi_id     = doi_id,
          email_type = email_type,
          recipient_email = recipient_email,
          sent_status = sent_status
          )
  
        count_result = result_list[0]
        count += int(count_result["Count"])
  
      # Now make a decision on how many emails counted
      if(count > 0):
        duplicate = True
      elif(count == 0):
        duplicate = False

    except:
      # Do nothing, we will return the default
      pass
    
    return duplicate
                      
  
  def get_authors(self, doi_id = None, corresponding = None, document = None):
    """
    Using the EJP data provider, get the column headings
    and author data, and reassemble into a list of authors
    document is only provided when running tests, otherwise just specify the doi_id
    """
    author_list = []
    (column_headings, authors) = self.ejp.get_authors(doi_id = doi_id, corresponding = corresponding, document = document)
    
    # Authors will be none if there is not data
    if authors is None:
      if(self.logger):
        self.logger.info("No authors found for article doi id " + doi_id)
      return None
    
    for author in authors:
      i = 0
      temp = {}
      for value in author:
        heading = column_headings[i]
        temp[heading] = value
        i = i + 1
      # Special: convert the dict to an object for use in templates
      obj = Struct(**temp)
      author_list.append(obj)
      
    return author_list
  
  def get_editors(self, doi_id = None, document = None):
    """
    Using the EJP data provider, get the column headings
    and editor data, and reassemble into a list of editors
    document is only provided when running tests, otherwise just specify the doi_id
    """
    editor_list = []
    (column_headings, editors) = self.ejp.get_editors(doi_id = doi_id, document = document)
    for editor in editors:
      i = 0
      temp = {}
      for value in editor:
        heading = column_headings[i]
        temp[heading] = value
        i = i + 1
      # Special: convert the dict to an object for use in templates
      obj = Struct(**temp)
      editor_list.append(obj)
      
    return editor_list

class Struct(object):
  def __init__(self, **entries):
    self.__dict__.update(entries)

