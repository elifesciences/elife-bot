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
from optparse import OptionParser

"""
Amazon SWF SendQueuedEmail starter
"""

class starter_SendQueuedEmail():

  def start(self, ENV = "dev", limit = None):
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)
    
    # Log
    identity = "starter_%s" % int(random.random() * 1000)
    logFile = "starter.log"
    #logFile = None
    logger = log.logger(logFile, settings.setLevel, identity)
    
    # Simple connect
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    
    # Start a workflow execution
    workflow_id = "SendQueuedEmail"
    workflow_name = "SendQueuedEmail"
    workflow_version = "1"
    child_policy = None
    execution_start_to_close_timeout = None

    if(limit):
      input = '{"data": {"limit": "' + limit + '"}}'
    else:
      input = None
    
    try:
      response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

      logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
      
    except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
      # There is already a running workflow with that ID, cannot start another
      message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
      print message
      logger.info(message)
      
if __name__ == "__main__":
  
  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  parser.add_option("-l", "--limit", default="100", action="store", type="string", dest="limit", help="set the limit of emails to send")
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env

  o = starter_SendQueuedEmail()

  o.start(ENV)