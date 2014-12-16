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

import provider.simpleDB as dblib

"""
Amazon SWF PublishArticle starter, for Fluidinfo API publishing
"""

class starter_FTPArticle():

  def start(self, ENV = "dev", workflow = None, doi_id = None):
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)
    
    # Log
    identity = "starter_%s" % int(random.random() * 1000)
    logFile = "starter.log"
    #logFile = None
    logger = log.logger(logFile, settings.setLevel, identity)
    
    # Simple connect
    conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
  
    if(doi_id is not None and workflow is not None):

      (workflow_id, workflow_name, workflow_version,
       child_policy, execution_start_to_close_timeout,
       input) = self.get_workflow_params(workflow, doi_id, settings)
  
      logger.info('Starting workflow: %s' % workflow_id)
      try:
        response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)
  
        logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
        
      except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
        # There is already a running workflow with that ID, cannot start another
        message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
        print message
        logger.info(message)
      
  def get_workflow_params(self, workflow, doi_id, settings):
    
    workflow_id = workflow_name = workflow_version = child_policy = execution_start_to_close_timeout = None
    # Setting timeout to 23 hours temporarily during article resupply
    execution_start_to_close_timeout = str(60*60*23)
    input = None
    
    if (workflow == "HWX"
        or workflow == "HWArchive"
        or workflow == 'PMCArchive'
        or workflow == 'NLMArchive'
        or workflow == 'HEFCE'):
      # Standard article bucket monitor
      bucket = settings.bucket
      workflow_id = "FTPArticle_" + workflow + "_" + str(doi_id)

    # workflow_id as set above
    workflow_id = workflow_id
    workflow_name = "FTPArticle"
    workflow_version = "1"
    
    data = {}
    data['workflow'] = workflow
    data['elife_id'] = doi_id
    
    input_json = {}
    input_json['data'] = data
    
    input = json.dumps(input_json)

    return (workflow_id, workflow_name, workflow_version, child_policy, execution_start_to_close_timeout, input)
      
      
  def get_docs_from_SimpleDB(self, ENV = "dev", doi_id = None):
    """
    Get the array of docs from the SimpleDB provider
    """
    docs = []
    
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)
    
    db = dblib.SimpleDB(settings)
    db.connect()
    
    if(doi_id is not None):
      xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "xml", latest = True, doi_id = doi_id)

    for x in xml_item_list:
      tmp = {}
      elife_id = str(x['name']).split("/")[0]
      document = 'https://s3.amazonaws.com/' + x['item_name']
      tmp['elife_id'] = elife_id
      tmp['document'] = document
      docs.append(tmp)
    
    return docs

if __name__ == "__main__":

  doi_id = None
  workflow = None

  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  parser.add_option("-w", "--workflow-name", default=None, action="store", type="string", dest="workflow", help="specify the workflow name to start")
  parser.add_option("-d", "--doi-id", default=None, action="store", type="string", dest="doi_id", help="specify the DOI id of a single article")
  
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env
  if options.workflow: 
    workflow = options.workflow
  if options.doi_id:
    doi_id = options.doi_id

  o = starter_FTPArticle()

  o.start(ENV, workflow = workflow, doi_id = doi_id)