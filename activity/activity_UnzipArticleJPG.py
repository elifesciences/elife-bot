import boto.swf
import json
import random
import datetime
import calendar
import time
import os

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib

"""
UnzipArticleJPG activity
"""

class activity_UnzipArticleJPG(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "UnzipArticleJPG"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Download a S3 object from the elife-articles bucket, unzip if necessary, and save to the elife-cdn bucket."
    
    # Create the filesystem provider
    self.fs = fslib.Filesystem(self.get_tmp_dir())
    
    self.elife_id = None
    self.document = None
    
    self.subfolder = 'jpg'
    self.content_type = None

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
    
    # The document location on local file system
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
      
      # Get an S3 key name for where to save each supplemental file
      s3key_name = self.get_jpg_object_S3key_name(elife_id, tmp_document)
      
      # Create S3 key and save the file there
      bucket_name = self.settings.cdn_bucket
      s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
      bucket = s3_conn.lookup(bucket_name)
      s3key = boto.s3.key.Key(bucket)
      s3key.key = s3key_name
      # Set Content-type metadata prior to upload
      if(self.content_type):
        s3key.set_metadata('Content-Type', self.content_type)
      s3key.set_contents_from_filename(tmp_doc_path, replace=True)
    
    if(self.logger):
      self.logger.info('UnzipArticleJPG: %s' % elife_id)

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
