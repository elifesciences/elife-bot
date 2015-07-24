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
import os
from optparse import OptionParser

import provider.simpleDB as dblib

"""
Amazon SWF PublicationEmail starter
"""

class starter_PublicationEmail():

    def start(self, ENV = "dev"):
        # Specify run environment settings
        settings = settingsLib.get_settings(ENV)
        
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)
        
        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    
        # Publication email variables
        allow_duplicates = False
        if(ENV == "dev"):
          # Dev workflow, set the default to allow duplicate emails
          allow_duplicates = True
          
        data = {}
        data["allow_duplicates"] = allow_duplicates
    
        # Start a workflow execution
        workflow_id = "PublicationEmail"
        workflow_name = "PublicationEmail"
        workflow_version = "1"
        child_policy = None
        execution_start_to_close_timeout = None
        input = '{"data": ' + json.dumps(data) + '}'

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
            
        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            print message
            logger.info(message)

if __name__ == "__main__":

    document = None
    
    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")

    (options, args) = parser.parse_args()
    if options.env: 
        ENV = options.env

    o = starter_PublicationEmail()

    o.start(ENV)