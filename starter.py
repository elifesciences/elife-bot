import boto.swf
import settings as settingsLib
import json
import random
import datetime

"""
Amazon SWF workflow starter
"""

def start(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	# Start a workflow execution
	workflow_id = "ping"
	#workflow_name = "PublishArticle"
	workflow_name = "Ping"
	workflow_version = "1"
	child_policy = None
	execution_start_to_close_timeout = None
	input = '{"data": "none"}'
	
	response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

	print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)
	
if __name__ == "__main__":
	start()