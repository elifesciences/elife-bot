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
from optparse import OptionParser

"""
Amazon SWF Sum workflow starter
"""

def start(ENV = "dev", workflow = "Sum"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Log
	identity = "starter_%s" % int(random.random() * 1000)
	logFile = "starter.log"
	#logFile = None
	logger = log.logger(logFile, settings.setLevel, identity)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
	if(workflow):
		(workflow_id, workflow_name, workflow_version, child_policy, execution_start_to_close_timeout, input) = get_workflow_params(workflow)

		logger.info('Starting workflow: %s' % workflow_id)
		try:
			response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

			logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
			
		except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
			# There is already a running workflow with that ID, cannot start another
			message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
			print message
			logger.info(message)

def get_workflow_params(workflow):
	
	workflow_id = workflow_name = workflow_version = child_policy = execution_start_to_close_timeout = None
	input = None
	
	if(workflow == "Sum"):
		workflow_id = "sum_%s" % int(random.random() * 10000)
		workflow_name = "Sum"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = None
		input = '{"data": [1,3,7,11]}'

	return (workflow_id, workflow_name, workflow_version, child_policy, execution_start_to_close_timeout, input)
	
if __name__ == "__main__":
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	start(ENV)