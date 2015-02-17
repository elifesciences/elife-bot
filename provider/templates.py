import json
import random
import datetime
import calendar
import time
from operator import itemgetter, attrgetter

from jinja2 import Template, Environment, FileSystemLoader

import boto.s3
from boto.s3.connection import S3Connection

import filesystem as fslib

"""
Templates provider
Connects to S3, discovers, downloads, and parses templates using jinja2
"""

class Templates(object):
  
  def __init__(self, settings = None, tmp_dir = None):
    self.settings = settings
    self.tmp_dir = tmp_dir
    
    # Default tmp_dir if not specified
    self.tmp_dir_default = "templates_provider"
    
    # Default S3 bucket name
    self.bucket_name = None
    if(self.settings is not None):
      self.bucket_name = self.settings.templates_bucket
    
    # Email template folder (prefix) in S3 bucket
    self.s3_email_templates_dir = "email_templates"
    
    # S3 connection
    self.s3_conn = None
    
    # Filesystem provider
    self.fs = None
    
    # Jinja stuff
    self.jinja_env = None
    
    # Track whether templates are downloaded and ready for use
    self.email_templates_warmed = False
    
  def connect(self):
    """
    Connect to S3 using the settings
    """
    s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
    self.s3_conn = s3_conn
    return self.s3_conn

  def get_bucket(self, bucket_name = None):
    """
    Using the S3 connection, lookup the bucket
    """
    if(self.s3_conn is None):
      s3_conn = self.connect()
    else:
      s3_conn = self.s3_conn
    
    if(bucket_name is None):
      # Use the object bucket_name if not provided
      bucket_name = self.bucket_name
    
    # Lookup the bucket
    bucket = s3_conn.lookup(bucket_name)

    return bucket

  def get_s3key(self, s3_key_name, bucket = None):
    """
    Get the S3 key from the bucket
    If the bucket is not provided, use the object bucket
    """
    if(bucket is None):
      bucket = self.get_bucket()
    
    s3key = bucket.get_key(s3_key_name)
    
    return s3key
    
  def get_fs(self):
    """
    For running tests, return the filesystem provider
    so it can be interrogated
    """
    if(self.fs is None):
      # Create the filesystem provider
      self.fs = fslib.Filesystem(self.get_tmp_dir())
    return self.fs
  
  def get_tmp_dir(self):
    """
    Get the temporary file directory, but if not set
    then make the directory
    """
    if(self.tmp_dir):
      return self.tmp_dir
    else:
      self.tmp_dir = self.tmp_dir_default
      
    return self.tmp_dir
    
  def get_email_templates_list(self):
    """
    Get a list of email templates to download
    in order to support author publication
    and editor publication emails
    """
    template_list = []
    template_list.append("email_header.html")
    template_list.append("email_footer.html")
    template_list.append("author_publication_email.html")
    template_list.append("author_publication_email.json")
    template_list.append("author_publication_email_Insight_to_VOR.html")
    template_list.append("author_publication_email_Insight_to_VOR.json")
    template_list.append("author_publication_email_POA.html")
    template_list.append("author_publication_email_POA.json")
    template_list.append("author_publication_email_VOR_after_POA.html")
    template_list.append("author_publication_email_VOR_after_POA.json")
    template_list.append("author_publication_email_VOR_no_POA.html")
    template_list.append("author_publication_email_VOR_no_POA.json")

    return template_list
  
  def download_email_templates_from_s3(self):
    """
    Prepare the tmp_dir jinja template directory
    to hold template files used in author publication
    and editor publication emails
    """
    template_list = self.get_email_templates_list()
    
    template_missing = False
    
    for t in template_list:
      success = self.download_template_from_s3(
        template_type = "email",
        template_name = t)
      if(not success):
        template_missing = True
        
    if(template_missing):
      self.email_templates_warmed = False
    elif(template_missing is False):
      self.email_templates_warmed = True
            
  def download_template_from_s3(self, template_type = None, template_name = None, s3_key_name = None):
    """
    Download a template from the S3 bucket to the
    tmp_dir, so it can be loaded by jinja
    """

    # If no specific s3_key_name supplied, assemble one
    if(s3_key_name is None):
      s3_key_name = self.get_s3_key_name(template_type, template_name)

    # Get the object by key and save it to the filesystem
    s3_key = self.get_s3key(s3_key_name)
    try:
      contents = s3_key.get_contents_as_string()
    except AttributeError:
      # File may be missing from S3 bucket
      contents = None
    
    if(contents is not None):
      self.save_template_contents_to_tmp_dir(template_name, contents)
      return True
    
    # Default
    return False

  def save_template_contents_to_tmp_dir(self, template_name, contents):
    """
    Given a template_name and UTF-8 content for a template,
    save it to the tmp_dir for later use
    Can be used from S3 object content, or local filesystem
    loaded content in the case of running tests
    """
    
    if(self.fs is None):
      self.fs = self.get_fs()
    
    if(contents is not None):
      self.fs.write_content_to_document(contents, template_name)
      return True
    
    # Default
    return False
    
  def get_s3_key_name(self, template_type, template_name):
    """
    Given a template type and template name, return the expected
    s3_key_name for an S3 object in the templates_bucket
    """
    s3_key_name = None
    delimiter = "/"
    
    if(template_type == "email"):
      # Email templates stored in email folder
      s3_key_name = self.s3_email_templates_dir + delimiter + template_name
      
    return s3_key_name
  
  def get_jinja_env(self):
    """
    Instantiate the jinja template environment
    if it does not already exist
    Use a file system loader from the tmp_dir as the root
    """

    if(self.jinja_env is None):
      loader = FileSystemLoader(self.get_tmp_dir())
      self.jinja_env = Environment(loader = loader)
    
    return self.jinja_env
  
  def get_jinja_template(self, jinja_env, template_name):
    
    template = jinja_env.get_template(template_name)
    
    return template
  
  def get_email_body(self, email_type, author, article, format = "html"):
    """
    Given the email type and data objects, load the jinja environment,
    get the template, render it and return the
    email body
    """

    # Warm the template files
    if(self.email_templates_warmed is not True):
      self.download_email_templates_from_s3()
      
    if(format == "html"):
      template_name = email_type + ".html"
    elif(format == "text"):
      template_name = email_type + ".txt"
      
    # Check again, in case the template warm was not successful
    if(self.email_templates_warmed is True):
  
      jinja_env = self.get_jinja_env()
      tmpl = self.get_jinja_template(jinja_env, template_name)
      body = tmpl.render(author = author, article = article)
      return body
    
    else:
      return None
      
  def get_email_headers(self, email_type, author, article, format = "html"):
    """
    Given the email type and data objects, load the jinja environment,
    get the template, render it and return the
    email headers
    """

    # Warm the template files
    if(self.email_templates_warmed is not True):
      self.download_email_templates_from_s3()
      
    template_name = email_type + ".json"
      
    # Check again, in case the template warm was not successful
    if(self.email_templates_warmed is True):
  
      jinja_env = self.get_jinja_env()
      tmpl = self.get_jinja_template(jinja_env, template_name)
      headers_str = tmpl.render(author = author, article = article)
      headers = json.loads(headers_str)
      print headers
      # Add the email format as specified
      headers["format"] = format
      return headers
    else:
      return None
    
  