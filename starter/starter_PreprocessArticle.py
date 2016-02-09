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
import os
from optparse import OptionParser

"""
Amazon SWF PreprocessArticle starter
"""

class starter_PreprocessArticle():

  def start(self, ENV = "dev", document = None):
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)
    
    # Log
    identity = "starter_%s" % int(random.random() * 1000)
    logFile = "starter.log"
    #logFile = None
    logger = log.logger(logFile, settings.setLevel, identity)
    
    # Simple connect
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
  
    (workflow_id, workflow_name, workflow_version,
     child_policy, execution_start_to_close_timeout,
     input) = self.get_workflow_params(settings, document)

    logger.info('Starting workflow: %s' % workflow_id)
    try:
      response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

      logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
      
    except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
      # There is already a running workflow with that ID, cannot start another
      message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
      print message
      logger.info(message)
      
  def get_workflow_params(self, settings, document = None):
    
    workflow_id = workflow_name = workflow_version = child_policy = execution_start_to_close_timeout = None
    # Setting timeout to 23 hours temporarily during article resupply
    execution_start_to_close_timeout = str(60*60*23)
    input = None
    
    if document:
      workflow_id = "PreprocessArticle_" + document.replace('/', '_')
    else:
      workflow_id = "PreprocessArticle"

    # workflow_id as set above
    workflow_id = workflow_id
    workflow_name = "PreprocessArticle"
    workflow_version = "1"
    
    if document:
      data = {}
      data['document'] = document
      
      input_json = {}
      input_json['data'] = data
    
      input = json.dumps(input_json)
    else:
      input = None

    return (workflow_id, workflow_name, workflow_version, child_policy, execution_start_to_close_timeout, input)


if __name__ == "__main__":

  document = None

  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  parser.add_option("-f", "--file", default=None, action="store", type="string", dest="document", help="specify the S3 object name of the zip file")
  
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env
  if options.document:
      document = options.document

  o = starter_PreprocessArticle()

  o.start(ENV, document = document)