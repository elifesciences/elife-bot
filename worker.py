import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
import importlib

import activity
#from activity import activity_PingWorker
#from activity import activity_Sum

"""
Amazon SWF worker
"""

def work(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Log
	identity = "worker_%s" % int(random.random() * 1000)
	#logFile = "worker.log"
	logFile = None
	logger = log.logger(logFile, settings.setLevel, identity)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	token = None

	# Poll for an activity task indefinitely
	while(True):
		if(token == None):
			logger.info('polling for activity...')
			activity_task = conn.poll_for_activity_task(settings.domain, settings.default_task_list, identity)
			logger.info('got activity: \n%s' % json.dumps(activity_task, sort_keys=True, indent=4))
			
			token = get_taskToken(activity_task)

			# Complete the activity based on data and activity type
			success = False
			if(token != None):
				# Get the activityType and attempt to do the work
				activityType = get_activityType(activity_task)
				if(activityType != None):
					logger.info('activityType: %s' % activityType)
				
					# Build a string for the object name
					activity_name = "activity_" + activityType
				
					# Attempt to import the module for the activity
					if(import_activity_class(activity_name)):
						# Instantiate the activity object
						activity_object = get_activity_object(activity_name, settings, logger)
				
						# Get the data to pass
						data = get_input(activity_task)
						
						# Do the activity
						success = activity_object.do_activity(data)
						
						# Print the result to the log
						logger.info('got result: \n%s' % json.dumps(activity_object.result, sort_keys=True, indent=4))

						# Complete the activity task if it was successful
						if(success == True):
							message = activity_object.result
							respond_completed(conn, logger, token, message)
						
					else:
						logger.info('error: could not load object %s\n' % activity_name)
						
		# Reset and loop
		token = None
		
def get_input(activity_task):
	"""
	Given a response from polling for activity from SWF via boto,
	extract the input from the json data
	"""
	try:
		data = json.loads(activity_task["input"])
	except KeyError:
		data = None
	return data
		
def get_taskToken(activity_task):
	"""
	Given a response from polling for activity from SWF via boto,
	extract the taskToken from the json data, if present
	"""
	try:
		return activity_task["taskToken"]
	except KeyError:
		# No taskToken returned
		return None
		
def get_activityType(activity_task):
	"""
	Given a polling for activity response from SWF via boto,
	extract the activityType from the json data
	"""
	try:
		return activity_task["activityType"]["name"]
	except KeyError:
		# No activityType found
		return None
	
def import_activity_class(activity_name):
	"""
	Given an activity subclass name as activity_name,
	attempt to lazy load the class when needed
	"""
	try:
		importlib.import_module("activity." + activity_name)
		return True
	except ImportError:
		return False

def get_activity_object(activity_name, settings, logger):
	"""
	Given an activity_name, and if the module class is already
	imported, create an object an return it
	"""
	full_path = "activity." + activity_name + "." + activity_name
	f = eval(full_path)
	# Create the object
	activity_object = f(settings, logger)
	return activity_object
		
def respond_completed(conn, logger, token, message):
	"""
	Given an SWF connection and logger as resources,
	the token to specify an accepted activity and a message
	to send, communicate with SWF that the activity was completed
	"""
	out = conn.respond_activity_task_completed(token,str(message))
	logger.info('respond_activity_task_completed returned %s' % out)

if __name__ == "__main__":
	work()

