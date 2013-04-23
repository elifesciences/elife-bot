import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
from optparse import OptionParser
import importlib
import workflow

"""
Amazon SWF register workflow or activity utility
"""

def start(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)

	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	workflow_names = []
	workflow_names.append("Ping")
	workflow_names.append("Sum")
	workflow_names.append("PublishArticle")

	for workflow_name in workflow_names:
		# Import the workflow libraries
		workflow_class_name = "workflow_" + workflow_name
		module_name = "workflow." + workflow_class_name
		importlib.import_module(module_name)
		full_path = "workflow." + workflow_class_name + "." + workflow_class_name
		# Create the workflow object
		f = eval(full_path)
		logger = None
		workflow_object = f(settings, logger, conn)
		
		# Now register it
		response = workflow_object.register()
	
		print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)
	
if __name__ == "__main__":
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	start(ENV)