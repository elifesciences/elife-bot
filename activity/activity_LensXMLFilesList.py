import boto.swf
import json
import random
import datetime
import calendar
import time
import requests
import os

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib
import provider.simpleDB as dblib

"""
LensXMLFilesList activity
"""

class activity_LensXMLFilesList(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "LensXMLFilesList"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Create the eLife Lens xml list file for cache warming, and then save those to the S3 CDN bucket."
    
    # Data provider
    self.db = dblib.SimpleDB(settings)
    
    # Create the filesystem provider
    self.fs = fslib.Filesystem(self.get_tmp_dir())

  def do_activity(self, data = None):
    """
    Do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    self.db.connect()
    
    xml_list_content = self.get_xml_list()
    
    filename = 'xml_files.txt'
    mode = "w+"
    f = self.fs.open_file_from_tmp_dir(filename, mode)
    f.write(xml_list_content)
    f.close
    
    # Save the document to the elife-lens bucket
    bucket_name = 'elife-lens'
    
    # Connect to S3
    s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
    # Lookup bucket
    bucket = s3_conn.lookup(bucket_name)

    # Create S3 key and save the file there
    s3key = boto.s3.key.Key(bucket)
    s3key.key = filename
    full_filename = self.get_tmp_dir() + os.sep + filename
    s3key.set_contents_from_filename(full_filename, replace=True)

    if(self.logger):
      self.logger.info('LensXMLFilesList: %s' % filename)
    
    return True

  def get_xml_list(self):
    """
    Generate the xml_files.txt content, a one per line list of .xml files
    """
    content = ""
    
    xml_item_list = self.db.elife_get_article_S3_file_items(file_data_type = "xml", latest = "True")
    sources = {}
    documents = []
    for x in xml_item_list:
      tmp = {}
      doi_id = str(x['name']).split("/")[0]
      url = 'https://s3.amazonaws.com/elife-cdn/elife-articles/' + doi_id + '/elife' + doi_id + '.xml'
      tmp['xml_url'] = url
      documents.append(tmp)

    for d in documents:
      content = content + d['xml_url'] + "\n"

    return content
