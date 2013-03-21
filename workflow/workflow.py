import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import json
import random
import datetime

"""
Amazon SWF workflow base class
"""

class workflow(object):
	# Base class for extending
	def __init__(self, settings, logger, conn = None, token = None, decision = None, maximum_page_size = 100, definition = None):
		self.settings = settings
		self.logger = logger
		self.definition = None
		if(definition != None):
			self.load_definition(definition)

	def load_definition(self, definition):
		"""
		Given a JSON representation of an entire workflow definition,
		as specified for processing a workflow, parse and load the data
		"""
		self.definition = definition

	def get_definition(self):
		"""
		Return a JSON represetation of the workflow definition,
		if present
		"""
		if(self.definition == None):
			return None
		return self.definition

	def complete_workflow(self):
		"""
		Signal the workflow is completed to SWF
		"""
		d = Layer1Decisions()
		d.complete_workflow_execution()
		self.complete_decision(d)
		#out = self.conn.respond_decision_task_completed(self.token,d._data)
		#self.logger.info('respond_decision_task_completed returned %s' % out)
		
	def complete_decision(self, d = None):
		"""
		Signal a decision was made to SWF
		"""
		if(d is None):
			d = Layer1Decisions()
		out = self.conn.respond_decision_task_completed(self.token,d._data)
		self.logger.info('respond_decision_task_completed returned %s' % out)

	def is_workflow_complete(self):
		"""
		Stub - TO DO!!!
		"""
		if(self.activity_status("Sum", self.decision) == True):
			return True

	def get_next_activities(self):
		"""
		Stub - TO DO!!!
		"""
		activities = []
		
		if(self.activity_status("PingWorker", self.decision) == False):
			activities.append(self.definition["steps"][0]["step1"])
		if(self.activity_status("Sum", self.decision) == False):
			activities.append(self.definition["steps"][1]["step2a"])
			
		return activities
		
	def schedule_activity(self, activity, d = None):
		"""
		Given a JSON representation for an activity,
		schedule an activity task into the Layer1Decisions
		object, then return it
		"""
		
		# Cast all values to string
		task_list = str(self.definition["task_list"])
		
		activity_id =  str(activity["activity_id"])
		#activity_id = activity_id + '.' + self.get_time() + '.%s' % int(random.random() * 10000)
		activity_type = str(activity["activity_type"])
		version = str(activity["version"])
		heartbeat_timeout = str(activity["heartbeat_timeout"])
		schedule_to_close_timeout = str(activity["schedule_to_close_timeout"])
		schedule_to_start_timeout = str(activity["schedule_to_start_timeout"])
		start_to_close_timeout = str(activity["start_to_close_timeout"])
		data = json.dumps(activity["input"])

		self.logger.info('scheduling task: %s' % activity_id)
		if(d is None):
			d = Layer1Decisions()
		d.schedule_activity_task(activity_id,           # Activity ID
														 activity_type,         # Activity Type
														 version,               # Activity Type Version
														 task_list,             # Task List
														 'control data',        # control
														 heartbeat_timeout,     # Heartbeat in seconds
														 schedule_to_close_timeout,                 # schedule_to_close_timeout
														 schedule_to_start_timeout,                 # schedule_to_start_timeout
														 start_to_close_timeout,                  # start_to_close_timeout
														 data)    # input: extra data to pass to activity
		return d
		
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
