import boto.swf
import settings as settingsLib
import json
import random
import datetime

"""
Amazon SWF worker
"""

def work(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	token = None

	# Poll for an activity task indefinitely
	while(True):
		if(token == None):
			print get_time() + 'polling for activity...'
			activity_task = conn.poll_for_activity_task(settings.domain, settings.default_task_list)
			print get_time() + 'got activity: \n%s' % json.dumps(activity_task, sort_keys=True, indent=4)
			
			try:
				token = activity_task["taskToken"]
			except KeyError:
				# No taskToken returned
				pass
	
		# Complete the activity based on data and activity type
		#  TO DO !!!!!!!!!!!!
	
		#------------------------------------------------------------------
		# Complete Activity task
		#  - easy enough
		if(token != None):
			task_status = get_time() + 'Thank-you, come again!'
			out = conn.respond_activity_task_completed(token,task_status)
			print get_time() + 'respond_activity_task_completed returned %s' % out
		#------------------------------------------------------------------
		
		# Reset and loop
		token = None

def get_time():
	"""
	Return the current time in UTC for logging
	"""
	return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

if __name__ == "__main__":
	work()

