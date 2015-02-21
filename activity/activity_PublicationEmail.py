import boto.swf
import json
import random
import datetime
import calendar
import time

from collections import namedtuple

import activity

import provider.simpleDB as dblib
import provider.templates as templatelib
import provider.ejp as ejplib
import provider.article as articlelib

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
    
    # Default is do not send duplicate emails
    self.allow_duplicates = False
    
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
    
    current_time = time.gmtime()
    current_timestamp = calendar.timegm(current_time)
    
    elife_id = data["data"]["elife_id"]
    # Check for whether the workflow execution was told to allow duplicate emails
    #  default is False
    try:
      self.allow_duplicates = data["data"]["allow_duplicates"]
    except KeyError:
      # Not specified? Ok, just use the default
      pass
    
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
    
    article = self.create_article(elife_id)
    
    # Ready to format emails and queue them
    
    # First send author emails
    authors = self.get_authors(doi_id = elife_id)

    # TODO!! Determine which email type to send
    email_type = "author_publication_email_VOR_no_POA"

    # Temporary for testing, send a test run
    self.send_email_testrun(self.email_types, elife_id, authors, article)
      
    return True
  
  def create_article(self, elife_id = None):
    """
    Instantiate an article object and optionally populate it with
    data for the elife_id (doi_id) supplied
    """
    
    # Instantiate a new article object
    article = articlelib.article(self.settings, self.get_tmp_dir())
    
    if elife_id:
      # Get and parse the article XML for data
      article.get_article_data(doi_id = elife_id)
    
    return article
  
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
        
      related_doi_id = article.get_doi_id(related_article_doi)
      
      related_article = self.create_article(related_doi_id)
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

