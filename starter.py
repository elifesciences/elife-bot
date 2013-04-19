import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
from optparse import OptionParser

"""
Amazon SWF workflow starter
"""

def start(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Log
	identity = "starter_%s" % int(random.random() * 1000)
	logFile = "starter.log"
	#logFile = None
	logger = log.logger(logFile, settings.setLevel, identity)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	for num in range(1):
		# Start a workflow execution
		workflow_id = "sum_%s" % int(random.random() * 10000)
		#workflow_name = "PublishArticle"
		workflow_name = "Sum"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = None
		input = '{"data": [1,3,7,11]}'
	
		response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

		logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
	
if __name__ == "__main__":
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	start(ENV)