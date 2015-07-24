import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import json
import random
import datetime
import time

"""
Amazon SWF workflow base class
"""

class workflow(object):
	# Base class for extending
	def __init__(self, settings, logger, conn = None, token = None, decision = None, maximum_page_size = 100, definition = None):
		self.settings = settings
		self.logger = logger
		self.conn = conn
		self.token = token
		self.decision = decision
		self.maximum_page_size = maximum_page_size
		self.definition = None
		if(definition != None):
			self.load_definition(definition)
			
		# SWF Defaults, most are set in derived classes or at runtime
		try:
			self.domain = self.settings.domain
		except KeyError:
			self.domain = None
			
		try:
			self.task_list = self.settings.default_task_list
		except KeyError:
			self.task_list = None

		self.name = None
		self.version = None
		self.default_child_policy = "TERMINATE"
		self.default_execution_start_to_close_timeout = 60*10
		self.default_task_start_to_close_timeout = 30
		self.description = None

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
		Check each step was completed to determine if workflow is complete
		"""
		for step in self.definition["steps"]:
			# Check for single or multiple activities in the step
			if(type(step) == list):
				# Is a list of activities to complete in parallel
				for p_activity in step:
					activityType = p_activity["activity_type"]
					activityID = p_activity["activity_id"]
					if(self.activity_status(self.decision, activityType, activityID) == False):
						return False
			else:
				# A single activity
				activityType = step["activity_type"]
				activityID = step["activity_id"]
				
				if(self.activity_status(self.decision, activityType, activityID) == False):
					return False
			
		return True

	def get_next_activities(self):
		"""
		For each step of a workflow, determine which activities are completed
		and return the activities to start next
		"""
		activities = []
		
		for step in self.definition["steps"]:
			# Check for single or multiple activities in the step
			if(type(step) == list):
				# Is a list of activities to complete in parallel
				# Check if the entire list of activities is completed
				all_completed = True
				none_started = True
				for p_activity in step:
					activityType = p_activity["activity_type"]
					activityID = p_activity["activity_id"]
					if(self.activity_status(self.decision, activityType, activityID) == False):
						all_completed = False
					if(self.activity_status(self.decision, activityType, activityID) == True):
						none_started = False
				if(all_completed == False and none_started == True):
					# A fresh step not started yet, add the activities
					for p_activity in step:
						activities.append(p_activity)
				
			else:
				# A single activity
				activityType = step["activity_type"]
				activityID = step["activity_id"]
				
				if(self.activity_status(self.decision, activityType, activityID) == False):
					# Only add one activity at a time, for now
					#if(len(activities) == 0):
					activities.append(step)
			
			# Return the activities not completed yet	
			if(len(activities) > 0):
				return activities

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

	def activity_status(self, decision, activityType = None, activityID = None):
		"""
		Given an activityType and/or activityID as the activity details, and
		a decision response from SWF, determine whether the
		activity was successfully run
		"""
	
		if(activityType is None and activityID is None):
			return False

		eventId_list = []

		for event in decision["events"]:
			eventId = None
			# Find the all matching eventID for the activityType and/or activityID
			if(activityType is not None and activityID is not None):
				try:
					if(event["activityTaskScheduledEventAttributes"]["activityType"]["name"] == activityType
						 and event["activityTaskScheduledEventAttributes"]["activityId"] == activityID):
						eventId_list.append(event["eventId"])
				except KeyError:
					pass
			elif(activityType is not None and activityID is None):
				try:
					if(event["activityTaskScheduledEventAttributes"]["activityType"]["name"] == activityType):
						eventId_list.append(event["eventId"])
				except KeyError:
					pass
			elif(activityID is not None and activityType is None):
				try:
					if(event["activityTaskScheduledEventAttributes"]["activityId"] == activityID):
						eventId_list.append(event["eventId"])
				except KeyError:
					pass
			
		# Now if we have an eventId, find if in the decision history is was
		#  successfully completed
		if(len(eventId_list) <= 0):
			return False
		for event in decision["events"]:
			for eventId in eventId_list:
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
	
	def last_activity_status(self, decision):
		"""
		Given a decision response from SWF, determine whether the
		last run activity Failed or Completed
		"""
		status = None
		# Traverse the array in reverse order
		for event in decision["events"][::-1]:
			if(event["eventType"] == "ActivityTaskCompleted"):
				status = "ActivityTaskCompleted"
				break
			elif(event["eventType"] == "ActivityTaskFailed"):
				status = "ActivityTaskFailed"
				break
				
		return status
	
	def handle_nextPageToken(self):
		# Quick test for nextPageToken
		try:
			if self.decision["nextPageToken"]:
				# nextPageToken should be paging if the decider is configured properly
				#  If there is a nextPageToken
				#  something has gone wrong and terminate the workflow execution with
				#  extreme prejudice
				d = Layer1Decisions()
				reason="nextPageToken found, maximum_page_size of " + str(self.maximum_page_size) + " exceeded"
				d.fail_workflow_execution(reason)
				out = self.conn.respond_decision_task_completed(self.token,d._data)
				self.logger.info(reason)
				self.logger.info('respond_decision_task_completed returned %s' % out)
				self.token = None
				return False
		except KeyError:
			# No nextPageToken, so we did not exceed the maximum_page_size, continue
			pass
		
	def get_input(self):
		"""
		From the decision response, which is JSON data form SWF, get the
		input data that started the workflow
		"""
		if(self.decision is None):
			return None
		try:
			input = json.loads(self.decision["events"][0]["workflowExecutionStartedEventAttributes"]["input"])
		except KeyError:
			input = None
		return input
	
	def rate_limit_failed_activity(self, decision):
		"""
		To slow down workflows with missing activity types,
		if the previous activity failed, wait for a bit
		"""
		try:
			if(self.last_activity_status(decision) == "ActivityTaskFailed"):
				time.sleep(10)
		except TypeError:
			pass

	def do_workflow(self, data = None):
		"""
		Make decisions and process the workflow accordingly
		"""
		
		# Quick test for nextPageToken
		self.handle_nextPageToken()

		# Schedule an activity
		if(self.token != None):
			# 1. Check if the workflow is completed
			if(self.is_workflow_complete()):
				# Complete the workflow execution
				self.complete_workflow()
			else:
				self.rate_limit_failed_activity(self.decision)
				# 2. Get the next activity
				next_activities = self.get_next_activities()
				d = None
				for activity in next_activities:
					# Schedule each activity
					d = self.schedule_activity(activity, d)
				self.complete_decision(d)
				
		return True
	
	def describe(self):
		"""
		Describe workflow type from SWF, to confirm it exists
		Requires object to have an active connection to SWF using boto
		"""
		if(self.conn == None or self.domain == None or self.name == None or self.version == None):
			return None
		
		try:
			response = self.conn.describe_workflow_type(self.domain, self.name, self.version)
		except boto.exception.SWFResponseError:
			response = None
		
		return response
	
	def register(self):
		"""
		Register the workflow type with SWF, if it does not already exist
		Requires object to have an active connection to SWF using boto
		"""
		if(self.conn == None or self.domain == None or self.name == None or self.version == None):
			return None
		
		if(self.describe() is None):
			response = self.conn.register_workflow_type(
				str(self.domain),
				str(self.name),
				str(self.version),
				str(self.task_list),
				str(self.default_child_policy),
				str(self.default_execution_start_to_close_timeout),
				str(self.default_task_start_to_close_timeout),
				str(self.description))
			return response