import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime

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
			
			try:
				token = activity_task["taskToken"]
			except KeyError:
				# No taskToken returned
				pass
	
			# Complete the activity based on data and activity type
			success = False
			if(token != None):
				# Get the activityType and attempt to do the work
				try:
					activityType = activity_task["activityType"]["name"]
					logger.info('activityType: %s' % activityType)
				except KeyError:
					continue
				
				# Call the function using eval
				try:
					function_name = "activity_" + activityType
					f = eval(function_name)
					success = f()
				except NameError:
					success = False
				logger.info('%s success %s' % (function_name, success))
				
		
				#------------------------------------------------------------------
				# Complete Activity task
				#  - easy enough
				if(success == True):
					message = 'Thank-you, come again!'
					respond_completed(conn, logger, token, message)

			#------------------------------------------------------------------
		
		# Reset and loop
		token = None
		
def activity_PingWorker(data = None):
	"""
	PingWorker activity, do the work, in this case
	just return true
	"""
	return True
		
def respond_completed(conn, logger, token, message):
	"""
	Given an SWF connection and logger as resources,
	the token to specify an accepted activity and a message
	to send, communicate with SWF that the activity was completed
	"""
	out = conn.respond_activity_task_completed(token,message)
	logger.info('respond_activity_task_completed returned %s' % out)

if __name__ == "__main__":
	work()

