import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
from optparse import OptionParser
import importlib
import workflow
import activity

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
		class_name = "workflow_" + workflow_name
		module_name = "workflow." + class_name
		importlib.import_module(module_name)
		full_path = "workflow." + class_name + "." + class_name
		# Create the workflow object
		f = eval(full_path)
		logger = None
		workflow_object = f(settings, logger, conn)
		
		# Now register it
		response = workflow_object.register()
	
		print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)
		
	activity_names = []
	activity_names.append("PingWorker")
	activity_names.append("Sum")
	activity_names.append("ArticleToFluidinfo")

	for activity_name in activity_names:
		# Import the activity libraries
		class_name = "activity_" + activity_name
		module_name = "activity." + class_name
		importlib.import_module(module_name)
		full_path = "activity." + class_name + "." + class_name
		# Create the workflow object
		f = eval(full_path)
		logger = None
		activity_object = f(settings, logger, conn)
		
		# Now register it
		response = activity_object.register()
	
		print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)
	
if __name__ == "__main__":
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	start(ENV)