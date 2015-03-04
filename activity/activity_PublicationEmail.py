import boto.swf
import json
import random
import datetime
import calendar
import time
import os
import arrow

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
    
    # Track the success of some steps
    self.activity_status = None
    
    # Track XML files selected for publication
    self.article_xml_filenames = []
    self.xml_file_to_doi_map = {}
    self.articles = []
    self.related_articles = []
    self.articles_approved = []
    self.articles_approved_prepared = []
    self.insight_articles_to_remove_from_outbox = []
    
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
    
    self.date_stamp = self.set_datestamp()
    
    self.admin_email_content = ''
    
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
      
      self.articles_approved_prepared = self.prepare_articles(self.articles_approved)
      
      if(self.logger):
        log_info = "Total parsed articles: " + str(len(self.articles))
        log_info += "\n" + "Total approved articles " + str(len(self.articles_approved))
        log_info += "\n" + "Total prepared articles " + str(len(self.articles_approved_prepared))
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
      
    # For the set of articles now select the template, authors and queue the emails
    for article in self.articles_approved_prepared:
      
      # Determine which email type or template to send
      email_type = self.choose_email_type(
          article_type = article.article_type,
          is_poa       = article.is_poa(),
          was_ever_poa = article.was_ever_poa
        )
      
      # Get the authors depending on the article type
      if article.article_type == "article-commentary":
        authors = self.get_authors(article.related_insight_article.doi_id)
      else:
        authors = self.get_authors(article.doi_id)
      
      # Send an email to each author
      for author in authors:
        self.send_email(email_type, article.doi_id, author, article)
      

      # Temporary for testing, send a test run - LATER FOR TESTING TEMPLATES
      #self.send_email_testrun(self.email_types, article.doi_id, authors, article)
    
    # Clean the outbox
    self.clean_outbox()
    
    # Send email to admins with the status
    self.activity_status = True
    self.send_admin_email()
    
    return True
  
  def set_datestamp(self):
      a = arrow.utcnow()
      date_stamp = str(a.datetime.year) + str(a.datetime.month).zfill(2) + str(a.datetime.day).zfill(2)
      return date_stamp
  
  def choose_email_type(self, article_type, is_poa, was_ever_poa):
    """
    Given some article details, we can choose the
    appropriate email template
    """
    email_type = None
    
    if article_type == "article-commentary":
      # Insight
      email_type = "author_publication_email_Insight_to_VOR"
      
    elif article_type == "research-article":
      if is_poa is True:
        # POA article
        email_type = "author_publication_email_POA"
        
      elif is_poa is False:
        # VOR article, decide based on if it was ever POA
        if was_ever_poa is True:
          email_type = "author_publication_email_VOR_after_POA"
          
        else:
          # False or None is allowed here
          email_type = "author_publication_email_VOR_no_POA"
    
    return email_type
  
  def prepare_articles(self, articles):
    """
    Given a set of article objects,
    decide whether its related article should be set
    Based on at least two factors,
      If the article is an Insight type of article,
      If both an Insight and its matching research article is in the set of articles
    Some Insight articles may be removed too
    """
    
    prepared_articles = []
    
    # Get a list of article DOIs for comparison later
    article_non_insight_doi_list = []
    article_insight_doi_list = []
    for article in articles:
      if article.article_type == "article-commentary":
        article_insight_doi_list.append(article.doi)
      else:
        article_non_insight_doi_list.append(article.doi)
    
    #print "Non-insight " + json.dumps(article_non_insight_doi_list)
    #print "Insight " + json.dumps(article_insight_doi_list)
    
    remove_article_doi = []
    
    # Process or delete articles as required
    for article in articles:
      #print article.doi + " is type " + article.article_type
      if article.article_type == "article-commentary":
        # Insight
        
        # Set the related article only if its related article is
        #  NOT in the list of articles DOIs
        # This means it is an insight for a VOR that was published previously
        related_article_doi = article.get_article_related_insight_doi()
        if related_article_doi in article_non_insight_doi_list:
          
          #print "Article match on " + article.doi
          
          # We do not want to send for this insight
          remove_article_doi.append(article.doi)
          # We also do not want to leave it in the outbox, add it to the removal list
          self.insight_articles_to_remove_from_outbox.append(article)
          
          
          # We do want to set the related article for its match
          for research_article in articles:
            if research_article.doi == related_article_doi:
              if(self.logger):
                log_info = "Setting match on " + related_article_doi + " to " + article.doi
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
              research_article.set_related_insight_article(article)
          
        else:
          # Set this insights related article
          
          #print "No article match on " + article.doi
          
          related_article_doi = article.get_article_related_insight_doi()
          if related_article_doi:
            related_article = self.get_related_article(related_article_doi)
            article.set_related_insight_article(related_article)
            
    # Can remove articles now if required
    for article in articles:
      if article.doi not in remove_article_doi:
        prepared_articles.append(article)
        
    return prepared_articles
    
  
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

  def download_templates(self):
    """
    Download the email templates from s3    
    """
    
    # Prepare email templates
    self.templates.download_email_templates_from_s3()
    if(self.templates.email_templates_warmed is not True):
      if(self.logger):
        log_info = 'PublicationEmail email templates did not warm successfully'
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
      # Stop now! Return False if we do not have the necessary files
      return False
    else:
      if(self.logger):
        log_info = 'PublicationEmail email templates warmed'
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
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
          log_info = "Hit the article cache on " + doi
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
        return article
    
    # Article for this DOI does not exist, populate it
    doi_id = int(doi.split(".")[-1])
    article = self.create_article(doi_id)
    
    self.related_articles.append(article)
    
    if(self.logger):
      log_info = "Building article for " + doi
      self.admin_email_content += "\n" + log_info
      self.logger.info(log_info)

    return article
  
  def approve_articles(self, articles):
    """
    Given a list of article objects, approve them for processing    
    """
    
    approved_articles = []
        
    # Keep track of which articles to remove at the end
    remove_article_doi = []
    
    # Remove based on article type
    for article in articles:
      if article.article_type in self.article_types_do_not_send:
        if(self.logger):
          log_info = "Removing based on article type " + article.doi
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
        remove_article_doi.append(article.doi)
        
    # Remove if display channel is "Feature article"
    for article in articles:
      if article.is_in_display_channel("Feature article") is True:
        if(self.logger):
          log_info = "Removing because display channel is Feature article " + article.doi
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
        remove_article_doi.append(article.doi)  

    # Create a blank article object to use its functions
    blank_article = self.create_article()
    # Remove based on published status
    
    for article in articles:
      # Article object knows if it is POA or not
      is_poa = article.is_poa()
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
    
    # Can remove the articles now without affecting the loops using del
    for article in articles:
      if article.doi not in remove_article_doi:
        approved_articles.append(article)

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
          log_info = ('Duplicate email: doi_id: %s email_type: %s recipient_email: %s'
                           % (elife_id, headers["email_type"], author.e_mail))
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
          
    # Secondly, check if article is on the do not send list
    if duplicate is False and self.allow_duplicates is not True:
      duplicate = self.is_article_do_not_send(elife_id)
      
      if(duplicate is True):
        if(self.logger):
          log_info = ('Article on do not send list for DOI: doi_id: %s email_type: %s recipient_email: %s'
                           % (elife_id, headers["email_type"], author.e_mail))
          self.admin_email_content += "\n" + log_info
          self.logger.info(log_info)
    
    # Now we can actually queue the email to be sent
    if(duplicate is False):
      # Queue the email
      if(self.logger):
        log_info = ("Sending " + email_type + " type email" +
                         " for article " + elife_id +
                         " to recipient_email " + author.e_mail)
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
      
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
    for article in self.articles_approved_prepared:
      remove_doi_list.append(article.doi)
    for article in self.insight_articles_to_remove_from_outbox:
      remove_doi_list.append(article.doi)
      
    for k, v in self.xml_file_to_doi_map.items():
      if k in remove_doi_list:
        processed_file_names.append(v)
    
    for name in processed_file_names:
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
        log_info = "No authors found for article doi id " + doi_id
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
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
  
  def is_article_do_not_send(self, doi_id):
    """
    Check if article is on the do not send email list
    This is used to not send a publication email when an article is correct
    For articles published prior to the launch of this publication email feature
      we cannot check the log of all emails sent to check if a duplicate
      email exists already
    """
    
    # Convert to string for matching
    if type(doi_id) == int:
      doi_id = str(doi_id).zfill(5)
    
    if doi_id in self.get_article_do_not_send_list():
      return True      
    else:
      return False
      
  def get_article_do_not_send_list(self):
    """
    Return list of do not send article DOI id
    """
    
    do_not_send_list = [
      "00003", "00005", "00007", "00011", "00012", "00013", "00031", "00036", "00047", "00048", 
      "00049", "00051", "00065", "00067", "00068", "00070", "00078", "00090", "00093", "00102", 
      "00105", "00109", "00116", "00117", "00133", "00160", "00170", "00171", "00173", "00178", 
      "00181", "00183", "00184", "00190", "00205", "00218", "00220", "00230", "00231", "00240", 
      "00242", "00243", "00247", "00248", "00260", "00269", "00270", "00278", "00281", "00286", 
      "00288", "00290", "00291", "00299", "00301", "00302", "00306", "00308", "00311", "00312", 
      "00321", "00324", "00326", "00327", "00329", "00333", "00334", "00336", "00337", "00340", 
      "00347", "00348", "00351", "00352", "00353", "00354", "00358", "00362", "00365", "00367", 
      "00378", "00380", "00385", "00386", "00387", "00400", "00411", "00415", "00421", "00422", 
      "00425", "00426", "00429", "00435", "00444", "00450", "00452", "00458", "00459", "00461", 
      "00467", "00471", "00473", "00475", "00476", "00477", "00481", "00482", "00488", "00491", 
      "00498", "00499", "00505", "00508", "00515", "00518", "00522", "00523", "00533", "00534", 
      "00537", "00542", "00558", "00563", "00565", "00569", "00571", "00572", "00573", "00577", 
      "00590", "00592", "00593", "00594", "00603", "00605", "00615", "00625", "00626", "00631", 
      "00632", "00633", "00638", "00639", "00640", "00641", "00642", "00646", "00647", "00648", 
      "00654", "00655", "00658", "00659", "00662", "00663", "00666", "00668", "00669", "00672", 
      "00675", "00676", "00683", "00691", "00692", "00699", "00704", "00708", "00710", "00712", 
      "00723", "00726", "00729", "00731", "00736", "00744", "00745", "00747", "00750", "00757", 
      "00759", "00762", "00767", "00768", "00772", "00776", "00778", "00780", "00782", "00785", 
      "00790", "00791", "00792", "00799", "00800", "00801", "00802", "00804", "00806", "00808", 
      "00813", "00822", "00824", "00825", "00828", "00829", "00842", "00844", "00845", "00855", 
      "00856", "00857", "00861", "00862", "00863", "00866", "00868", "00873", "00882", "00884", 
      "00886", "00895", "00899", "00903", "00905", "00914", "00924", "00926", "00932", "00933", 
      "00940", "00943", "00947", "00948", "00951", "00953", "00954", "00958", "00960", "00961", 
      "00963", "00966", "00967", "00969", "00971", "00983", "00992", "00994", "00996", "00999", 
      "01004", "01008", "01009", "01020", "01029", "01030", "01042", "01045", "01061", "01064", 
      "01067", "01071", "01074", "01084", "01085", "01086", "01089", "01096", "01098", "01102", 
      "01104", "01108", "01114", "01115", "01119", "01120", "01123", "01127", "01133", "01135", 
      "01136", "01138", "01139", "01140", "01149", "01157", "01159", "01160", "01169", "01179", 
      "01180", "01197", "01201", "01202", "01206", "01211", "01213", "01214", "01221", "01222", 
      "01228", "01229", "01233", "01234", "01236", "01239", "01252", "01256", "01257", "01267", 
      "01270", "01273", "01279", "01287", "01289", "01291", "01293", "01294", "01295", "01296", 
      "01298", "01299", "01305", "01308", "01310", "01311", "01312", "01319", "01322", "01323", 
      "01326", "01328", "01339", "01340", "01341", "01345", "01350", "01355", "01369", "01370", 
      "01374", "01381", "01385", "01386", "01387", "01388", "01402", "01403", "01412", "01414", 
      "01426", "01428", "01433", "01434", "01438", "01439", "01440", "01456", "01457", "01460", 
      "01462", "01465", "01469", "01473", "01479", "01481", "01482", "01483", "01488", "01489", 
      "01494", "01496", "01498", "01501", "01503", "01514", "01515", "01516", "01519", "01524", 
      "01530", "01535", "01539", "01541", "01557", "01561", "01566", "01567", "01569", "01574", 
      "01579", "01581", "01584", "01587", "01596", "01597", "01599", "01603", "01604", "01605", 
      "01607", "01608", "01610", "01612", "01621", "01623", "01630", "01632", "01633", "01637", 
      "01641", "01658", "01659", "01662", "01663", "01671", "01680", "01681", "01684", "01694", 
      "01695", "01699", "01700", "01710", "01715", "01724", "01730", "01738", "01739", "01741", 
      "01749", "01751", "01754", "01760", "01763", "01775", "01776", "01779", "01808", "01809", 
      "01812", "01816", "01817", "01820", "01828", "01831", "01832", "01833", "01834", "01839", 
      "01845", "01846", "01849", "01856", "01857", "01861", "01867", "01873", "01879", "01883", 
      "01888", "01892", "01893", "01901", "01906", "01911", "01913", "01914", "01916", "01917", 
      "01926", "01928", "01936", "01939", "01944", "01948", "01949", "01958", "01963", "01964", 
      "01967", "01968", "01977", "01979", "01982", "01990", "01993", "01998", "02001", "02008", 
      "02009", "02020", "02024", "02025", "02028", "02030", "02040", "02041", "02042", "02043", 
      "02046", "02053", "02057", "02061", "02062", "02069", "02076", "02077", "02078", "02087", 
      "02088", "02094", "02104", "02105", "02109", "02112", "02115", "02130", "02131", "02137", 
      "02148", "02151", "02152", "02164", "02171", "02172", "02181", "02184", "02189", "02190", 
      "02196", "02199", "02200", "02203", "02206", "02208", "02217", "02218", "02224", "02230", 
      "02236", "02238", "02242", "02245", "02252", "02257", "02260", "02265", "02270", "02272", 
      "02273", "02277", "02283", "02286", "02289", "02304", "02313", "02322", "02324", "02349", 
      "02362", "02365", "02369", "02370", "02372", "02375", "02384", "02386", "02387", "02391", 
      "02394", "02395", "02397", "02403", "02407", "02409", "02419", "02439", "02440", "02443", 
      "02444", "02445", "02450", "02451", "02475", "02478", "02481", "02482", "02490", "02501", 
      "02504", "02510", "02511", "02515", "02516", "02517", "02523", "02525", "02531", "02535", 
      "02536", "02555", "02557", "02559", "02564", "02565", "02576", "02583", "02589", "02590", 
      "02598", "02615", "02618", "02619", "02626", "02630", "02634", "02637", "02641", "02653", 
      "02658", "02663", "02667", "02669", "02670", "02671", "02674", "02676", "02678", "02687", 
      "02715", "02725", "02726", "02730", "02734", "02736", "02740", "02743", "02747", "02750", 
      "02755", "02758", "02763", "02772", "02777", "02780", "02784", "02786", "02791", "02792", 
      "02798", "02805", "02809", "02811", "02812", "02813", "02833", "02839", "02840", "02844", 
      "02848", "02851", "02854", "02860", "02862", "02863", "02866", "02872", "02875", "02882", 
      "02893", "02897", "02904", "02907", "02910", "02917", "02923", "02935", "02938", "02945", 
      "02949", "02950", "02951", "02956", "02963", "02964", "02975", "02978", "02981", "02993", 
      "02996", "02999", "03005", "03007", "03011", "03023", "03025", "03031", "03032", "03035", 
      "03043", "03058", "03061", "03068", "03069", "03075", "03077", "03080", "03083", "03091", 
      "03100", "03104", "03110", "03115", "03116", "03125", "03126", "03128", "03145", "03146", 
      "03159", "03164", "03176", "03178", "03180", "03185", "03191", "03197", "03198", "03205", 
      "03206", "03222", "03229", "03233", "03235", "03239", "03245", "03251", "03254", "03255", 
      "03271", "03273", "03275", "03282", "03285", "03293", "03297", "03300", "03307", "03311", 
      "03318", "03342", "03346", "03348", "03351", "03357", "03363", "03371", "03372", "03374", 
      "03375", "03383", "03385", "03397", "03398", "03399", "03401", "03405", "03406", "03416", 
      "03421", "03422", "03427", "03430", "03433", "03435", "03440", "03443", "03464", "03467", 
      "03468", "03473", "03475", "03476", "03487", "03496", "03497", "03498", "03502", "03504", 
      "03521", "03522", "03523", "03526", "03528", "03532", "03542", "03545", "03549", "03553", 
      "03558", "03563", "03564", "03568", "03573", "03574", "03575", "03579", "03581", "03582", 
      "03583", "03587", "03596", "03600", "03602", "03604", "03606", "03609", "03613", "03626", 
      "03635", "03638", "03640", "03641", "03648", "03650", "03653", "03656", "03658", "03663", 
      "03665", "03671", "03674", "03676", "03678", "03679", "03680", "03683", "03695", "03696", 
      "03697", "03701", "03702", "03703", "03706", "03711", "03714", "03720", "03722", "03724", 
      "03726", "03727", "03728", "03735", "03737", "03743", "03751", "03753", "03754", "03756", 
      "03764", "03765", "03766", "03772", "03778", "03779", "03781", "03785", "03790", "03804", 
      "03811", "03819", "03821", "03830", "03842", "03848", "03851", "03868", "03881", "03883", 
      "03891", "03892", "03895", "03896", "03908", "03915", "03925", "03939", "03941", "03943", 
      "03949", "03952", "03962", "03970", "03971", "03977", "03978", "03980", "03981", "03997", 
      "04000", "04006", "04008", "04014", "04024", "04034", "04037", "04040", "04046", "04047", 
      "04057", "04059", "04066", "04069", "04070", "04094", "04105", "04106", "04111", "04114", 
      "04120", "04121", "04123", "04126", "04132", "04135", "04137", "04147", "04158", "04165", 
      "04168", "04177", "04180", "04187", "04193", "04205", "04207", "04220", "04234", "04235", 
      "04236", "04246", "04247", "04249", "04251", "04263", "04265", "04266", "04273", "04279", 
      "04287", "04288", "04300", "04316", "04333", "04353", "04363", "04366", "04371", "04378", 
      "04380", "04387", "04389", "04390", "04395", "04402", "04406", "04415", "04418", "04433", 
      "04437", "04449", "04476", "04478", "04489", "04491", "04494", "04499", "04501", "04506", 
      "04517", "04525", "04530", "04531", "04534", "04543", "04551", "04553", "04563", "04565", 
      "04577", "04580", "04581", "04586", "04591", "04600", "04601", "04603", "04605", "04617", 
      "04629", "04630", "04631", "04645", "04660", "04664", "04686", "04692", "04693", "04711", 
      "04729", "04741", "04742", "04766", "04775", "04779", "04785", "04801", "04806", "04811", 
      "04851", "04854", "04869", "04875", "04876", "04878", "04885", "04889", "04901", "04902", 
      "04909", "04919", "04969", "04970", "04986", "04995", "04996", "04997", "04998", "05000", 
      "05007", "05025", "05031", "05033", "05041", "05048", "05055", "05060", "05075", "05087", 
      "05105", "05115", "05116", "05125", "05151", "05161", "05169", "05178", "05179", "05198", 
      "05216", "05218", "05244", "05256", "05259", "05269", "05289", "05290", "05334", "05352", 
      "05375", "05377", "05394", "05401", "05418", "05419", "05422", "05427", "05438", "05490", 
      "05504", "05508", "05553", "05558", "05564", "05570", "05580", "05597", "05614", "05657", 
      "05663", "05720", "05770", "05787", "05789", "05816", "05846", "05896", "05983", "06156", 
      "06193", "06200", "06235", "06303", "06306", "06351", "06424", "06430", "06453", "06494", 
      "06656", "06720", "06740", "06900", "06986"]
    
    return do_not_send_list
    
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
    

class Struct(object):
  def __init__(self, **entries):
    self.__dict__.update(entries)

