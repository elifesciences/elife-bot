import os
# Add parent directory for imports
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
Cron job to check for new article S3 supplemental and start workflows
"""

class cron_NewS3Suppl(object):

  def start(self, ENV = "dev"):
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)
    
    ping_marker_id = "cron_NewS3Suppl"
    
    # Log
    logFile = "starter.log"
    logger = log.logger(logFile, settings.setLevel, ping_marker_id)
    
    # Data provider
    db = dblib.SimpleDB(settings)
    db.connect()
    
    # SWF meta data provider
    swfmeta = swfmetalib.SWFMeta(settings)
    swfmeta.connect()
    
    # Default, if cron never run before
    last_startTimestamp = 0
    
    # Get the last time this cron was run
    last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(workflow_id = ping_marker_id)
  
    # Start a ping workflow as a marker
    self.start_ping_marker(ping_marker_id, ENV)
  
    # Check for S3 Suppl files that were updated since the last run
    date_format = "%Y-%m-%dT%H:%M:%S.000Z"
    
    # Quick hack - subtract 30 minutes to not ignore the top of the hour
    #   the time between S3Monitor running and this cron starter
    last_startTimestamp_minus_30 = last_startTimestamp - (60*30)
    if(last_startTimestamp_minus_30 < 0):
      last_startTimestamp_minus_30 = 0
    time_tuple = time.gmtime(last_startTimestamp_minus_30)
    
    last_startDate = time.strftime(date_format, time_tuple)
    
    logger.info('last run %s' % (last_startDate))
    
    S3_item_list = db.elife_get_article_S3_file_items(file_data_type = "suppl", latest = True, last_updated_since = last_startDate)
    
    logger.info('Suppl files updated since %s: %s' % (last_startDate, str(len(S3_item_list))))
  
    if(len(S3_item_list) <= 0):
      # No new SVG
      pass
    else:
      # Found new SVG files
      
      # Start a PublishSVG starter
      try:
        starter_name = "starter_PublishSuppl"
        self.import_starter_module(starter_name, logger)
        s = self.get_starter_module(starter_name, logger)
        s.start(ENV = ENV, last_updated_since = last_startDate)
      except:
        logger.info('Error: %s starting %s' % (ping_marker_id, starter_name))
        logger.exception('')

  def start_ping_marker(self, workflow_id, ENV = "dev"):
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
  
  def get_starter_module(self, starter_name, logger = None):
    """
    Given an starter_name, and if the starter module is already
    imported, load the module and return it
    """
    full_path = "starter." + starter_name + "." + starter_name + "()"
    f = None
    
    try:
      f = eval(full_path)
    except:
      if(logger):
        logger.exception('')
    
    return f
  
  def import_starter_module(self, starter_name, logger = None):
    """
    Given an starter name as starter_name,
    attempt to lazy load the module when needed
    """
    try:
      module_name = "starter." + starter_name
      importlib.import_module(module_name)
      return True
    except ImportError:
      if(logger):
        logger.exception('')
      return False

if __name__ == "__main__":
  
  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env

  o = cron_NewS3Suppl()

  o.start(ENV)