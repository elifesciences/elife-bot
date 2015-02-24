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
    self.article_data = None
    self.related_insight_article = None
    
    # Store the list of DOI id that was ever PoA
    self.was_poa_doi_ids = None
    
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
    
    document = open(filename, "rb")
    parsed = self.parse_article_xml(document)
    document.close()
    
    return parsed

  def parse_article_xml(self, document):
    """
    Given article XML, parse
    it and return an object representation
    """
    
    try:
      soup = self.parse_document(document)
      self.doi = self.parse_doi(soup)
      if(self.doi):
        self.doi_id = self.get_doi_id(self.doi)
        self.doi_url = self.get_doi_url(self.doi)
        self.lens_url = self.get_lens_url(self.doi)
        self.tweet_url = self.get_tweet_url(self.doi)
  
      self.pub_date = self.parse_pub_date(soup)
      if(self.pub_date):
        self.pub_date_timestamp = self.get_pub_date_timestamp(self.pub_date)
      
      self.article_title = self.parse_article_title(soup)
      self.article_type = self.parse_article_type(soup)
      
      self.related_articles = self.parse_related_article(soup)
      
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
    
  def get_was_poa_doi_ids(self, force = False):
      """
      Connect to the S3 bucket, and from the files in the published folder,
      get a list of .xml files, and then parse out the article id
      """
      # Return from cached values if not force
      if force is False and self.was_poa_doi_ids is not None:
          return self.was_poa_doi_ids
      
      was_poa_doi_ids = []
      poa_published_folder = "published/"

      file_extensions = []
      file_extensions.append(".xml")
      
      bucket_name = self.settings.poa_packaging_bucket
      
      # Connect to S3 and bucket
      s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
      bucket = s3_conn.lookup(bucket_name)
      
      delimiter = '/'
      headers = None
      
      # Step one, get all the subfolder names
      folders = []
      bucketList = bucket.list(prefix = poa_published_folder, delimiter = delimiter, headers = headers)
      for item in bucketList:
          if(isinstance(item, boto.s3.prefix.Prefix)):
              folders.append(item)

      # Step two, for each subfolder get the keys inside it
      s3_poa_key_names = []
      for folder_name in folders:
          prefix = folder_name.name
          
          # print "getting s3 keys from " + prefix
          
          s3_key_names = s3lib.get_s3_key_names_from_bucket(
              bucket          = bucket,
              prefix          = prefix,
              file_extensions = file_extensions)
          for s3_key_name in s3_key_names:
              s3_poa_key_names.append(s3_key_name)

      # Extract just the doi_id portion
      for s3_key_name in s3_poa_key_names:
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
      of the article XML file
      E.g.
        published/20140508/elife_poa_e02419.xml = 2419
        published/20140508/elife_poa_e02444v2.xml = 2444
      """
      
      doi_id = None
      delimiter = '/'
      file_name_prefix = "elife_poa_e"
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
    
  def is_poa(self):
      # Based the presence of an pub date whether it is a
      #  PoA article or VoR article
      date_type = "pub"

      if hasattr(self, "pub_date"):
        if self.pub_date is None:
          # No date means is POA
          return True
        else:
          # Found a date is not POA
          return False
      else:
        # Article XML was never parsed
        return None
    
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
          
    elif self.article_type == "insight":
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
          (is_poa is False and was_ever_poa is False)):
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
    
  """
  Some quick copy and paste from elife-api-prototype parseNLM.py parser to get the basics for now
  """
  
  def parse_document(self, document):
    return self.parse_xml(document)
  
  def parse_xml(self, xml):
    soup = BeautifulSoup(xml, ["lxml", "xml"])
    return soup
  
  def parse_doi(self, soup):
    doi = None
    doi_tags = self.extract_nodes(soup, "article-id", attr = "pub-id-type", value = "doi")
    for tag in doi_tags:
      # Only look at the doi tag directly inside the article-meta section
      if (tag.parent.name == "article-meta"):
        doi = tag.text
    return doi
  
  def parse_pub_date(self, soup, date_type = "pub"):
    """
    Find the publishing date for populating
    pub_date_date, pub_date_day, pub_date_month, pub_date_year, pub_date_timestamp
    Default pub_type is ppub, but will revert to epub if tag is not found
    """
    tz = "UTC"
    
    try:
      pub_date_section = self.extract_nodes(soup, "pub-date", attr = "date-type", value = date_type)
      if(len(pub_date_section) == 0):
        if(date_type == "ppub"):
          date_type = "epub"
        pub_date_section = self.extract_nodes(soup, "pub-date", attr = "pub-type", value = date_type)
      (day, month, year) = self.get_ymd(pub_date_section[0])
  
    except(IndexError):
      # Tag not found, try the other
      return None
    
    date_string = None
    try:
      date_string = time.strptime(year + "-" + month + "-" + day + " " + tz, "%Y-%m-%d %Z")
    except(TypeError):
      # Date did not convert
      pass
  
    return date_string
    
  def parse_article_title(self, soup):
    title_text = self.extract_node_text(soup, "article-title")
    return title_text
    
  def extract_first_node(self, soup, nodename):
    tags = self.extract_nodes(soup, nodename)
    try:
      tag = tags[0]
    except(IndexError):
      # Tag not found
      return None
    return tag
    
  def extract_nodes(self, soup, nodename, attr = None, value = None):
    tags = soup.find_all(nodename)
    if(attr != None and value != None):
      # Further refine nodes by attributes
      tags_by_value = []
      for tag in tags:
        try:
          if tag[attr] == value:
            tags_by_value.append(tag)
        except KeyError:
          continue
      return tags_by_value
    return tags
  
  def extract_node_text(self, soup, nodename, attr = None, value = None):
    """
    Extract node text by nodename, unless attr is supplied
    If attr and value is specified, find all the nodes and search
      by attr and value for the first node
    """
    tag_text = None
    if(attr == None):
      tag = self.extract_first_node(soup, nodename)
      try:
        tag_text = tag.text
      except(AttributeError):
        # Tag text not found
        return None
    else:
      tags = self.extract_nodes(soup, nodename, attr, value)
      for tag in tags:
        try:
          if tag[attr] == value:
            tag_text = tag.text
        except KeyError:
          continue
    return tag_text
  
  def get_ymd(self, soup):
    """
    Get the year, month and day from child tags
    """
    day = self.extract_node_text(soup, "day")
    month = self.extract_node_text(soup, "month")
    year = self.extract_node_text(soup, "year")
    return (day, month, year)
      
  def parse_article_type(self, soup):
      """
      Find the article_type from the article tag root XML attribute
      """
      article_type = None
      article = self.extract_nodes(soup, "article")
      #try:
      article_type = article[0]['article-type']    
      #except(KeyError,IndexError):
          # Attribute or tag not found
      #    return None
      return article_type
      
  def parse_related_article(self, soup):
    related_articles = []
    # Only look for type DOI for now, to find commentary articles
    related_article_tags = self.extract_nodes(soup, "related-article", attr = "ext-link-type", value = "doi")
    for tag in related_article_tags:
      # Only look at the doi tag directly inside the article-meta section
      if (tag.parent.name == "article-meta"):
        ra = {}
        ra["ext_link_type"] = tag["ext-link-type"]
        ra["related_article_type"] = tag["related-article-type"]
        ra["xlink_href"] = tag["xlink:href"]
        related_articles.append(ra)
        
    return related_articles
