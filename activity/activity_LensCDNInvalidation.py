import boto.swf
import json
import random
import datetime
import calendar
import time
import requests
import os

import activity

import boto

import provider.simpleDB as dblib

"""
LensCDNInvalidation activity
"""

class activity_LensCDNInvalidation(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "LensCDNInvalidation"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Create an invalidation request for the eLife Lens documents in the Cloudfront CDN."
    
    # Data provider
    self.db = dblib.SimpleDB(settings)

  def do_activity(self, data = None):
    """
    Do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    self.db.connect()
    
    # cdn.elifesciences.org CDN ID
    distribution_id = self.settings.cdn_distribution_id
    
    invalidation_list = self.get_invalidation_list()
    
    # Connect to S3
    c_conn = boto.connect_cloudfront(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
    
    # Limit of 1000 URLs to invalidate at one time
    try:
      count = int(len(invalidation_list) / 1000) + 1
    except:
      # Divide by zero or something else
      return False

    array_of_invalidation_list = self.split_array(invalidation_list, count)

    for i_list in array_of_invalidation_list:
      inval_req = c_conn.create_invalidation_request(distribution_id, invalidation_list)

    if(self.logger):
      self.logger.info('LensCDNInvalidation: %s' % "")
    
    return True

  def split_array(self, arr, count):
    """
    Split an array arr into count sub arrays
    """
    return [arr[i::count] for i in range(count)]

  def get_invalidation_list(self):
    """
    Get a list of files for invalidation on the CDN
    """
    
    xml_item_list = self.db.elife_get_article_S3_file_items(file_data_type = "xml", latest = True)

    documents = []
    url = 'documents/elife/documents.json'
    documents.append(url)
    url = 'documents/elife/documents.js'
    documents.append(url)

    # Disabled invalidating all files as the default, can provide this as an option later
    """
    for x in xml_item_list:
      doi_id = str(x['name']).split("/")[0]
      url = 'documents/elife/' + doi_id + '.json'
      documents.append(url)

      url = 'documents/elife/' + doi_id + '.js'
      documents.append(url)
    """
    
    return documents
