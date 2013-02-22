import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import os
import json
import random
import datetime

# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

"""
Amazon SWF workflow base class
"""

class workflow(object):
	# Base class for extending
	def __init__(self, settings, logger):
		self.settings = settings
		self.logger = logger

	def get_time(self):
		"""
		Return the current time in UTC for logging
		"""
		return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

	def activity_status(self, activityType, decision):
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
	
	def handle_nextPageToken(self):
		# Quick test for nextPageToken
		try:
			if self.decision["nextPageToken"]:
				# Currently no pagination of event history implemented, so if we have
				#  more than maximum_page_size of events, typically 1000, then assume
				#  something has gone wrong and terminate the workflow execution with
				#  extreme prejudice
				d = Layer1Decisions()
				reason="maximum_page_size of " + str(self.maximum_page_size) + " exceeded"
				d.fail_workflow_execution(reason)
				out = self.conn.respond_decision_task_completed(self.token,d._data)
				self.logger.info(reason)
				self.logger.info('respond_decision_task_completed returned %s' % out)
				self.token = None
				return False
		except KeyError:
			# No nextPageToken, so we did not exceed the maximum_page_size, continue
			pass
