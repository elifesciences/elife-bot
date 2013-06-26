import os
# Add parent directory for imports, so activity classes can use elife-api-prototype
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import time
import importlib
from optparse import OptionParser

import provider.simpleDB as dblib
import provider.swfmeta as swfmetalib
import starter

"""
Cron job to check for new article S3 XML and start workflows
"""

def start(ENV = "dev"):
  # Specify run environment settings
  settings = settingsLib.get_settings(ENV)
  
  ping_marker_id = "cron_NewS3XML"
  
  # Log
  logFile = "starter.log"
  logger = log.logger(logFile, settings.setLevel, ping_marker_id)
  
  # Data provider
  db = dblib.SimpleDB(settings)
  db.connect()
  
  # SWF meta data provider
  swfmeta = swfmetalib.SWFMeta(settings)
  swfmeta.connect()
  
  last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(workflow_id = ping_marker_id)

  # Start a ping workflow as a marker
  start_ping_marker(ping_marker_id, ENV)

  # Check for S3 XML files that were updated since the last run
  date_format = "%Y-%m-%dT%H:%M:%S.000Z"
  time_tuple = time.gmtime(last_startTimestamp)
  last_startDate = time.strftime(date_format, time_tuple)

  xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "xml", latest = True, last_updated_since = last_startDate)
  if(len(xml_item_list) <= 0):
    # No new XML
    pass
  else:
    # Found new XML files
    
    # Start a Fluidinfo PublishArticle starter
    try:
      starter_name = "starter_PublishArticle"
      import_starter_module(starter_name)
      s = get_starter_module(starter_name)
      s.start(ENV = ENV, last_updated_since = last_startDate)
    except:
      logger.info('Error: %s starting %s' % (ping_marker_id, module_name))
      logger.exception('')
    
    # Start a LensArticlePublish starter
    try:
      starter_name = "starter_LensArticlePublish"
      import_starter_module(starter_name)
      s = get_starter_module(starter_name)
      s.start(ENV = ENV, all = True)
    except:
      logger.info('Error: %s starting %s' % (ping_marker_id, module_name))
      logger.exception('')
    
    # Start a LensIndexPublish starter
    try:
      starter_name = "starter_LensIndexPublish"
      import_starter_module(starter_name)
      s = get_starter_module(starter_name)
      s.start(ENV = ENV)
    except:
      logger.info('Error: %s starting %s' % (ping_marker_id, module_name))
      logger.exception('')

def start_ping_marker(workflow_id, ENV = "dev"):
  """
  Start a ping workflow with a unique name to serve as a time marker
  for determining last time this was run
  """
  
  # Specify run environment settings
  settings = settingsLib.get_settings(ENV)
  
  workflow_id = workflow_id
  workflow_name = "Ping"
  workflow_version = "1"
  child_policy = None
  execution_start_to_close_timeout = None
  input = None

  conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
  try:
    response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

  except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
    # There is already a running workflow with that ID, cannot start another
    message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
    print message

def get_starter_module(starter_name):
  """
  Given an starter_name, and if the starter module is already
  imported, load the module and return it
  """
  full_path = "starter." + starter_name
  f = eval(full_path)
  return f

def import_starter_module(starter_name):
  """
  Given an starter name as starter_name,
  attempt to lazy load the module when needed
  """
  try:
    module_name = "starter." + starter_name
    importlib.import_module(module_name)
    return True
  except ImportError:
    return False

if __name__ == "__main__":
  
  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env

  start(ENV)