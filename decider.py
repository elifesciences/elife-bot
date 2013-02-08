import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import settings as settingsLib
import json
import random
import datetime

"""
Amazon SWF decider
"""

def decide(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	token = None

	# Poll for a decision task
	while(True):
		if(token == None):
			print 'polling for decision...'
			decision = conn.poll_for_decision_task(settings.domain, settings.default_task_list)
			print 'got decision: \n%s' % json.dumps(decision, sort_keys=True, indent=4)
			
			try:
				token = decision["taskToken"]
			except KeyError:
				# No taskToken returned
				pass
		
		# Make a decision to schedule an activity based on history
		#  TO DO !!!!!!!!!!!!
		
		# Schedule an activity
		if(token != None):
			if(activity_status("PingWorker", decision) == False):
				#activity_id='S3ZipToFluidinfo-task-%s' % int(random.random() * 10000)
				#activity_type = 'S3ZipToFluidinfo'
				activity_id='PingWorker.ActivityTask.' + get_time() + '.%s' % int(random.random() * 10000)
				activity_type = 'PingWorker'
				print '===> scheduling task: %s' % activity_id
				d = Layer1Decisions()
				d.schedule_activity_task(activity_id,           # Activity ID
																 activity_type,         # Activity Type
																 '1',                   # Activity Type Version
																 settings.default_task_list,                  # Task List(use default)
																 'control data',        # control
																 '300',                 # Heartbeat in seconds
																 '300',                 # schedule_to_close_timeout
																 '300',                 # schedule_to_start_timeout
																 '300',                  # start_to_close_timeout
																 '{data: "_"}')    # input: extra data to pass to activity
				#------------------------------------------------------------------
				# Complete Decision Task
				#  - easy enough
				if(d is None):
					d = Layer1Decisions()
				out = conn.respond_decision_task_completed(token,d._data)
				print '===> respond_decision_task_completed returned %s' % out
				#------------------------------------------------------------------
			
			else:
				# Complete the workflow execution
				d = Layer1Decisions()
				d.complete_workflow_execution()
				#out = conn.respond_decision_task_completed(token,d._data)
				#message = "Done."
				out = conn.respond_decision_task_completed(token,d._data)
				print '===> respond_decision_task_completed returned %s' % out
				
		# Reset and loop
		token = None
		
def activity_status(activityType, decision):
	"""
	Given an activityType as the name of activity, and
	a decision response from SWF, determine whether the
	acitivity was successfully run
	"""
	eventId = None
	for event in decision["events"]:
		# Find the first matching eventID for the activityType
		try:
			if(event["activityTaskScheduledEventAttributes"]["activityType"]["name"] == activityType):
				eventId = event["eventId"]
				break
		except KeyError:
			pass
	# Now if we have an eventId, find if in the decision history is was
	#  successfully completed
	if(eventId == None):
		return False
	for event in decision["events"]:
		# Find the first matching eventID for the activityType
		try:
			if(event["activityTaskCompletedEventAttributes"]["scheduledEventId"] == eventId):
				# Found matching data, now check completion
				if(event["eventType"] == "ActivityTaskCompleted"):
					# Good!
					return True
				break
		except KeyError:
			pass
	# Default
	return False

def get_time():
	"""
	Return the current time in UTC for logging
	"""
	return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

if __name__ == "__main__":
	decide()