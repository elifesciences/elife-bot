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

"""
Amazon SWF LensIndexPublish starter
"""

class starter_LensIndexPublish():

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
	
		start = True
	
		# Start a workflow execution
		workflow_id = "LensIndexPublish"
		workflow_name = "LensIndexPublish"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = str(60*45)
		input = None
	
		if(start):
			response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)
	
			logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

if __name__ == "__main__":

	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	o = starter_LensIndexPublish()

	o.start(ENV)