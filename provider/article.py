from bs4 import BeautifulSoup
import json
import random
import datetime
import calendar
import time
import os
import re
import requests
import zipfile
from operator import itemgetter, attrgetter

import urllib

import boto.s3
from boto.s3.connection import S3Connection

import simpleDB as dblib
import provider.s3lib as s3lib
from elifetools import parseJATS as parser

"""
Article data provider
From article XML, get some data for use in workflows and templates
"""

class article(object):
  
  def __init__(self, settings = None, tmp_dir = None):
    self.settings = settings
    self.tmp_dir = tmp_dir
    
    # Default tmp_dir if not specified
    self.tmp_dir_default = "article_provider"
    
    # SimpleDB connection for looking up S3 keys
    self.db = None
    if(self.settings is not None):
      # Data provider
      self.db = dblib.SimpleDB(settings)
    
    # S3 connection
    self.s3_conn = None
    
    # Default S3 bucket name
    self.bucket_name = None
    if(self.settings is not None):
      self.bucket_name = self.settings.bucket
    
    # Some defaults
    self.related_insight_article = None
    self.was_ever_poa = None
    self.is_poa = None
    
    # Store the list of DOI id that was ever PoA
    self.was_poa_doi_ids = None
    self.article_bucket_published_dates = None
    
    # For checking published articles need a URL prefix for where to check
    self.lookup_url_prefix = "http://elifesciences.org/lookup/doi/10.7554/eLife."
        
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

  def parse_article_file(self, filename):
    """
    Given a filename to an article XML
    parse it
    """
    
    parsed = self.parse_article_xml(filename)
    
    return parsed

  def parse_article_xml(self, document):
    """
    Given article XML, parse
    it and return an object representation
    """
    
    try:
      soup = parser.parse_document(document)
      self.doi = parser.doi(soup)
      if(self.doi):
        self.doi_id = self.get_doi_id(self.doi)
        self.doi_url = self.get_doi_url(self.doi)
        self.lens_url = self.get_lens_url(self.doi)
        self.tweet_url = self.get_tweet_url(self.doi)
  
      self.pub_date = parser.pub_date(soup)
      self.pub_date_timestamp = parser.pub_date_timestamp(soup)
  
      self.article_title = parser.title(soup)
      self.article_type = parser.article_type(soup)
      
      self.authors = parser.authors(soup)
      self.authors_string = self.authors_string(self.authors)
      
      self.related_articles = parser.related_article(soup)
      
      self.is_poa = parser.is_poa(soup)
      
      #self.subject_area = self.parse_subject_area(soup)
      
      self.display_channel = parser.display_channel(soup)
          
      return True
    except:
      return False
  
  def download_article_xml_from_s3(self, doi_id = None):
    """
    Return the article data for use in templates
    """
    
    download_dir = "s3_download"
    xml_filename = None
    # Check for the document

    # Convert the value just in case
    if type(doi_id) == int:
      doi_id = str(doi_id).zfill(5)

    # Connect to SimpleDB and get the latest article XML S3 object name
    self.db.connect()
    # Look up the latest XMl file by doi_id, should return a list of 1
    log_item = self.db.elife_get_article_S3_file_items(file_data_type = "xml", doi_id = doi_id, latest = True)
    s3_key_name = None
    
    try:
      s3_key_name = log_item[0]["name"]
    except IndexError:
      return False
    #print s3_key_name

    # Download from S3
    s3_key = self.get_s3key(s3_key_name)
    filename = s3_key_name.split('/')[-1]
    filename_plus_path = self.get_tmp_dir() + os.sep + filename
    #print filename_plus_path
    f = open(filename_plus_path, "wb")
    s3_key.get_contents_to_file(f)
    f.close()
    
    # Unzip
    z = zipfile.ZipFile(filename_plus_path)
    for f in z.namelist():
      # Expecting one file only per zip file in article XML zip
      z.extract(f, self.get_tmp_dir())
      xml_filename = f

    return xml_filename
    
  
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
    
    
  def get_tweet_url(self, doi):
    """
    Given a DOI, return a tweet URL
    """
    doi_url = self.get_doi_url(doi)
    f = {"text": doi_url}
    tweet_url ="http://twitter.com/intent/tweet?" + urllib.urlencode(f)
    return tweet_url
    
  def get_doi_url(self, doi):
    """
    Given a DOI, get the URL for the DOI
    """
    doi_url ="http://dx.doi.org/" + doi
    return doi_url
    
  def get_lens_url(self, doi):
    """
    Given a DOI, get the URL for the lens article
    """
    doi_id = self.get_doi_id(doi)
    lens_url = "http://lens.elifesciences.org/" + doi_id
    return lens_url
    
  def get_doi_id(self, doi):
    """
    Given a DOI, return the doi_id part of it
    e.g. DOI 10.7554/eLife.00013
    split on dot and the last list element is doi_id
    """
    x = doi.split(".")
    doi_id = x[-1]
    return doi_id
  
  def get_pub_date_timestamp(self, pub_date):
    """
    Given a time struct for a publish date
    parse and return a timestamp for it
    """
    timestamp = None
    try:
      timestamp = calendar.timegm(pub_date)
    except(TypeError):
      # Date did not convert
      pass
    return timestamp
    
  def set_related_insight_article(self, article):
    """
    If this article is type insight, then set the article
    the insight relates to here
    """
    self.related_insight_article = article
    
  def get_article_bucket_published_dates(self, force = False, folder_names = None, s3_key_names = None):
      """
      Connect to the S3 bucket, and from the files in the pubmed published folder,
      get a list of .xml files, parse out the article id, the date of the folder
      and the type of publication (POA or VOR)
        folder_names and s3_key_names is only supplied for when running automated tests
      """
      # Return from cached values if not force
      if force is False and self.article_bucket_published_dates is not None:
          return self.article_bucket_published_dates
      
      article_bucket_published_dates = {}
      poa_published_folder = "pubmed/published/"

      file_extensions = []
      file_extensions.append(".xml")
      
      bucket_name = self.settings.poa_packaging_bucket
      
      if folder_names is None:
          # Get the folder names from live s3 bucket if no test data supplied
          folder_names = self.get_folder_names_from_bucket(
                                  bucket_name = bucket_name,
                                  prefix      = poa_published_folder )
      
      if s3_key_names is None:
          # Get the s3 key names from live s3 bucket if no test data supplied
          s3_key_names = []
          for folder_name in folder_names:
              
              key_names = self.get_s3_key_names_from_bucket(
                                  bucket_name = bucket_name,
                                  prefix = folder_name,
                                  file_extensions = file_extensions)
          
              for key_name in key_names:
                s3_key_names.append(key_name)
      
      # Extract just the doi_id portion
      for s3_key_name in s3_key_names:
          # Try to get DOI from a POA key name first
          doi_id = self.get_doi_id_from_poa_s3_key_name(s3_key_name)
          if doi_id is not None:
            pub_date_type = "poa"
          else:
            doi_id = self.get_doi_id_from_s3_key_name(s3_key_name)
            if doi_id is not None:
              pub_date_type = "vor"
          
          if doi_id:
            
            # Create the dict if it does not exist
            try:
              article_bucket_published_dates[doi_id]
            except KeyError:
              article_bucket_published_dates[doi_id] = {}
            
            # Parse and save the date from the folder name
            date_string = self.get_date_string_from_s3_key_name(
              s3_key_name, poa_published_folder)
            
            date_obj = time.strptime(date_string, "%Y%m%d")
            
            # Compare so we have the earliest date saved
            current_date_obj = None
            try:
              current_date_obj = article_bucket_published_dates[doi_id][pub_date_type]
            except KeyError:
              current_date_obj = None
              
            if current_date_obj is None or date_obj < current_date_obj:
              # No date yet or it is previous to the current date, use this date
               article_bucket_published_dates[doi_id][pub_date_type] = date_obj
                  
      # Cache it
      self.article_bucket_published_dates = article_bucket_published_dates
      
      # Return it
      return article_bucket_published_dates
    
  def get_date_string_from_s3_key_name(self, s3_key_name, prefix):
      """
      Extract the folder name that is formatted like a date string
      from published folders in the s3 bucket for when workflows were run
      """
      date_string = None
      delimiter = '/'
      try:
          # Split on prefix
          s3_key = s3_key_name.split(prefix)[-1]
          # Split on delimiter
          parts = s3_key.split(delimiter)
          # First part is the date string
          date_string = parts[0]
      except:
          date_string = None
          
      return date_string
    
  def get_article_bucket_pub_date(self, doi, pub_event_type = None):
      """
      Given an article DOI, get its publication date
      Primarily this is important for POA articles and gets their publication date
        from S3 bucket data, because POA XML does not include a publication date
      For VOR articles instead parse the VOR article XML to get the date
      """
      
      doi_id = self.get_doi_id(doi)
      
      if self.article_bucket_published_dates is None:
        self.get_article_bucket_published_dates()
      
      try:
        if pub_event_type is not None:
          pub_dates = self.article_bucket_published_dates[int(doi_id)]
          pub_date = pub_dates[pub_event_type.lower()]

          #print time.strftime("%Y-%m-%dT%H:%M:%S.000Z", pub_date)
          return pub_date
        else:
          # No pub date type specified, this is the default return value
          return None

      except KeyError:
        # If the hash key does not exist then we just do not know
        return None
    
    
  def get_was_poa_doi_ids(self, force = False, folder_names = None, s3_key_names = None):
      """
      Connect to the S3 bucket, and from the files in the published folder,
      get a list of .xml files, and then parse out the article id
        folder_names and s3_key_names is only supplied for when running automated tests
      """
      # Return from cached values if not force
      if force is False and self.was_poa_doi_ids is not None:
          return self.was_poa_doi_ids
      
      was_poa_doi_ids = []
      poa_published_folder = "published/"

      file_extensions = []
      file_extensions.append(".xml")
      
      bucket_name = self.settings.poa_packaging_bucket
      
      if folder_names is None:
          # Get the folder names from live s3 bucket if no test data supplied
          folder_names = self.get_folder_names_from_bucket(
                                  bucket_name = bucket_name,
                                  prefix      = poa_published_folder )
          
      
      if s3_key_names is None:
          # Get the s3 key names from live s3 bucket if no test data supplied
          s3_key_names = []
          for folder_name in folder_names:
              
              key_names = self.get_s3_key_names_from_bucket(
                                  bucket_name = bucket_name,
                                  prefix = folder_name,
                                  file_extensions = file_extensions)
          
              for key_name in key_names:
                s3_key_names.append(key_name)
      
      # Extract just the doi_id portion
      for s3_key_name in s3_key_names:
          doi_id = self.get_doi_id_from_poa_s3_key_name(s3_key_name)
          if doi_id:
              was_poa_doi_ids.append(doi_id)
              
      # Remove duplicates and sort it
      was_poa_doi_ids = list(set(was_poa_doi_ids))
      was_poa_doi_ids.sort()
      
      # Cache it
      self.was_poa_doi_ids = was_poa_doi_ids
      
      # Return it
      return was_poa_doi_ids
    
  def get_folder_names_from_bucket(self, bucket_name, prefix):
    """
    Use live s3 bucket connection to get the folder names
    from the bucket. This is so functions that rely on the data
    can use test data when running automated tests
    """
    folder_names = None
    # Connect to S3 and bucket
    s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
    bucket = s3_conn.lookup(bucket_name)
    
    # Step one, get all the subfolder names
    folder_names = s3lib.get_s3_key_names_from_bucket(
            bucket          = bucket,
            key_type        = "prefix",
            prefix          = prefix)
    
    return folder_names
  
  def get_s3_key_names_from_bucket(self, bucket_name, prefix, file_extensions):
    """
    Use live s3 bucket connection to get the s3 key names
    from the bucket. This is so functions that rely on the data
    can use test data when running automated tests
    """
    s3_key_names = None
    # Connect to S3 and bucket
    s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
    bucket = s3_conn.lookup(bucket_name)
    
    s3_key_names = s3lib.get_s3_key_names_from_bucket(
        bucket          = bucket,
        key_type        = "key",
        prefix          = prefix,
        file_extensions = file_extensions)
    
    return s3_key_names
    
  def check_was_ever_poa(self, doi):
      """
      For each article XML downloaded from S3, check if it is published
      """
      
      doi_id = self.get_doi_id(doi)
      
      if int(doi_id) in self.get_was_poa_doi_ids():
          return True
      else:
          return False
    
  def get_doi_id_from_poa_s3_key_name(self, s3_key_name):
      """
      Extract just the integer doi_id value from the S3 key name
      of the article XML file for a poa XML file
      E.g.
        published/20140508/elife_poa_e02419.xml = 2419
        published/20140508/elife_poa_e02444v2.xml = 2444
      """
      
      doi_id = None
      delimiter = '/'
      file_name_prefix = "elife_poa_e"
      
      doi_id = self.get_doi_id_from_s3_key_name(s3_key_name, file_name_prefix)

      return doi_id
      
    
  def get_doi_id_from_s3_key_name(self, s3_key_name, file_name_prefix = "elife"):
      """
      Extract just the integer doi_id value from the S3 key name
      of the article XML file
      E.g. when file_name_prefix is "elife_poa_e"
        published/20140508/elife_poa_e02419.xml = 2419
        published/20140508/elife_poa_e02444v2.xml = 2444
      E.g. when file_name_prefix is "elife" (for VOR article XML files)
        pubmed/published/20140508/elife02419.xml = 2419
      """
      
      doi_id = None
      delimiter = '/'
      try:
          # Split on delimiter
          file_name_with_extension = s3_key_name.split(delimiter)[-1]
          # Remove file extension
          file_name = file_name_with_extension.split(".")[0]
          # Remove file name prefix
          file_name_id = file_name.split(file_name_prefix)[-1]
          # Get the numeric part of the file name
          doi_id = int("".join(re.findall(r'^\d+', file_name_id)))
      except:
          doi_id = None
          
      return doi_id
        
  def get_article_related_insight_doi(self):
    """
    Given an article object, depending on the article_type,
    look in the list of related_articles for a particular related_article_type
    and return one article DOI only (if there are multiple return the first)
    """
    
    if self.article_type == "research-article":
      for related in self.related_articles:
        if related["related_article_type"] == "commentary":
          return related["xlink_href"]
          
    elif self.article_type == "article-commentary":
      for related in self.related_articles:
        if related["related_article_type"] == "commentary-article":
          return related["xlink_href"]
          
    # Default
    return None
    
  def check_is_article_published(self, doi, is_poa, was_ever_poa, article_url = None):
      """
      For each article XML downloaded from S3, check if it is published
      Also needs to know whether the article is POA or was ever POA'ed
        article_url can be supplied for testing without making live HTTP requests
          and also accepts the value "Test_None" for running tests on a value of None
      """
      
      doi_id = int(self.get_doi_id(doi))

      if article_url == "Test_None":
        # For running tests, convert this value to None now it is important
        article_url = None
      else:
        # Not running tests
        if article_url is None:
          article_url = self.get_article_canonical_url(doi_id)
        #print article_url
        
        # Parse the URL based on the type of article
        if article_url is None:
            return None
          
          
      # Knowing the article_url status now continue with additional comparisons
      if (is_poa is True or
          (is_poa is False and was_ever_poa is False) or
          (is_poa is False and was_ever_poa is None)):
          # In this case, any URL is sufficient
          if article_url:
              return True
          else:
              return False
      elif is_poa is False and was_ever_poa is True:
          # In the case of was ever PoA but is not PoA
          #  check the URL does not contain the string "early"
          if article_url:
              if re.match('.*early.*', article_url) is None:
                  return True
              else:
                  return False
          else:
            return False
      
  def get_article_canonical_url(self, doi_id):
      """
      Given the doi_id, and using the lookup URL prefix,
      make an HTTP head request and return the URL after
      all redirects are followed
      """
      # Construct the lookup URL on the HW site
      lookup_url = self.get_article_lookup_url(doi_id)
      #print lookup_url
      
      r = requests.head(lookup_url, allow_redirects=True)
      if r.status_code == requests.codes.ok:
          return r.url
      else:
          return None
      return None
  
  def get_article_lookup_url(self, doi_id):
      """
      Given the doi_id, create the lookup URL
      """
      lookup_url = self.lookup_url_prefix + str(doi_id).zfill(5)
      return lookup_url
    
  def authors_string(self, authors):
    """
    Given a list of authors return a string for all the article authors    
    """
    
    authors_string = ""
    for author in authors:
      if authors_string != "":
        authors_string += ", "
      authors_string += author["given_names"] + " " + author["surname"]
      
    return authors_string
  
  def is_in_display_channel(self, display_channel):
    """
    Given a display channel to match, return True or False if
    the article display_channel list includes it
    """
    
    if not hasattr(self, "display_channel"):
      # Display channel was never set
      return None
    
    if display_channel in self.display_channel:
      return True
    else:
      return False
