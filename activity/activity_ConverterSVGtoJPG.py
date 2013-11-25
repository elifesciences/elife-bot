import boto.swf
import json
import random
import datetime
import calendar
import time
import os

import base64
from bs4 import BeautifulSoup

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib

"""
ConverterSVGtoJPG activity
"""

class activity_ConverterSVGtoJPG(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "ConverterSVGtoJPG"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Extract base64 image data from SVG and save as JPG: Download a S3 object from the elife-articles bucket, unzip if necessary, convert each, and save to the elife-cdn bucket."
    
    # Create the filesystem provider
    self.fs = fslib.Filesystem(self.get_tmp_dir())
    
    self.elife_id = None
    self.document = None
    
    self.subfolder = 'jpg'
    self.content_type = 'image/jpeg'

  def do_activity(self, data = None):
    """
    Do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    elife_id = self.get_elife_id_from_data(data)
    
    # Download the S3 object
    document = self.get_document_from_data(data)
    self.read_document_to_content(document)
    
    # The document(s) location(s) on local file system
    tmp_document_path = self.get_document()
    
    # Check for single or multiple files
    tmp_document_path_list = []
    if (type(tmp_document_path) == list):
      # A list, assign it
      tmp_document_path_list = tmp_document_path
    elif (tmp_document_path):
      # A single document, add it to the list
      tmp_document_path_list.append(tmp_document_path)
    
    for tmp_doc_path in tmp_document_path_list:
      # Clean up to get the filename alone
      tmp_document = self.get_document_name_from_path(tmp_doc_path)
      
      # Attempt to convert the SVG to JPG
      image_base64_data = self.get_image_data(tmp_document)
      
      if(image_base64_data is None):
        # Something in the conversion went wrong
        if(self.logger):
          self.logger.info('ConverterSVGtoJPG: Error converting %s' % tmp_document)
      else:
        # Assemble the JPG file name
        jpg_filename = self.get_jpg_filename(tmp_document)
        # Decode the base64 encoded data to binary data
        jpg_data = self.decode_base64_data(image_base64_data)
        if(jpg_data is None):
          # Something in the conversion went wrong
          if(self.logger):
            self.logger.info('ConverterSVGtoJPG: Error converting base64 data %s' % tmp_document)
        else:
          # Save the JPG file to disk
          self.fs.write_content_to_document(jpg_data, jpg_filename, mode = "wb")
          # Get the full path of the JPG file
          jpg_doc_path = self.get_tmp_dir() + os.sep + jpg_filename
          # Get an S3 key name for where to save each SVG file
          s3key_name = self.get_jpg_object_S3key_name(elife_id, jpg_filename)
          
          # Create S3 key and save the file there
          bucket_name = self.settings.cdn_bucket
          s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
          bucket = s3_conn.lookup(bucket_name)
          s3key = boto.s3.key.Key(bucket)
          s3key.key = s3key_name
          # Set Content-type metadata prior to upload
          if(self.content_type):
            s3key.set_metadata('Content-Type', self.content_type)
          s3key.set_contents_from_filename(jpg_doc_path, replace=True)
    
    if(self.logger):
      self.logger.info('ConverterSVGtoJPG: %s' % elife_id)

    return True
  
  def get_fs(self):
    """
    For running tests, return the filesystem provider
    so it can be interrogated
    """
    return self.fs
  
  def read_document_to_content(self, document, filename = None):
    """
    Exposed for running tests
    """
    self.fs.write_document_to_tmp_dir(document, filename)
    content = []

    for doc in self.fs.get_document():
      content.append(doc)

    return content

  def get_document(self):
    """
    Exposed for running tests
    """
    full_filename_list = []
    
    # Check for a list
    doc_list = []
    if (type(self.fs.get_document()) == list):
      doc_list = self.fs.get_document()
    else:
      doc_list.append(self.fs.get_document())
      
    for doc in doc_list:
      full_filename = None
      if(self.fs.tmp_dir):
        full_filename = self.fs.tmp_dir + os.sep + doc
      else:
        full_filename = doc
        
      if(full_filename):
        full_filename_list.append(full_filename)

    return full_filename_list
  
  def get_elife_id_from_data(self, data):
     self.elife_id = data["data"]["elife_id"]
     return self.elife_id

  def get_document_from_data(self, data):
     self.document = data["data"]["document"]
     return self.document

  def get_jpg_object_S3key_name(self, elife_id, document):
    """
    Given the elife_id (5 digits) and document name, assemble
    an S3 key (prefix for folder name, document for file name)
    """
    document = document.replace("/", '')
    delimiter = self.settings.delimiter
    prefix = delimiter + 'elife-articles' + delimiter + elife_id
    s3key_name = prefix + delimiter + self.subfolder + delimiter + document
    
    return s3key_name
    
  def get_document_name_from_path(self, document_path):
    """
    Given a document location in the tmp directory
    slice away everything but the filename and return it
    """
    document = document_path.replace(self.get_tmp_dir(), '')
    document = document.replace("", '')
    document = document.replace("\\", '')
    return document

  def get_jpg_filename(self, svg_filename):
    """
    Given the SVG filename, concatenate the new JPG filename
    """
    jpg_filename = ""
    x = svg_filename.split(".")
  
    base_filename = x[0]

    jpg_filename = base_filename + ".jpg"
    
    return jpg_filename

  def get_image_data(self, svg_filename):
    """
    From an SVG file containing a single <image> tag and
    with base64 jpg data in xlink:href attribute, return
    the base64 data
    """
    image_base64_data = None
    
    fh = self.fs.open_file_from_tmp_dir(svg_filename, "rb")
    content = fh.read()
    fh.close()
    
    soup = self.parse_document(content)
    image_nodes = self.get_image_tags(soup)
    if(len(image_nodes) > 1):
      # Too many nodes for the easy converter
      return None
    try:
      image_base64_data = image_nodes[0]["xlink:href"]
  
      # Strip out first bit
      image_base64_data = image_base64_data.replace("data:image/jpeg;base64,", "")
    except IndexError:
      # Tag or attribute missing, will return None
      pass
  
    return image_base64_data

  def decode_base64_data(self, image_base64_data):
    """
    Decode the base64 data
    """
    jpg_data = None
    try:
      jpg_data = base64.decodestring(image_base64_data)
    except:
      # Could be Incorrect padding error
      # Do nothing for now
      pass
    return jpg_data

  def get_image_tags(self, soup):
     image_nodes = self.extract_nodes(soup, "image")
     return image_nodes

  def parse_document(self, content):
    return self.parse_xml(content)
  
  def parse_xml(self, xml):
    soup = BeautifulSoup(xml, "lxml")
    return soup

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
