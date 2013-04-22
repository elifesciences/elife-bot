import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import json
import random
import datetime

import workflow

"""
PublishArticle workflow
"""

class workflow_PublishArticle(workflow.workflow):
	
	def __init__(self, settings, logger, conn = None, token = None, decision = None, maximum_page_size = 100):
		self.settings = settings
		self.logger = logger
		self.conn = conn
		self.token = token
		self.decision = decision
		self.maximum_page_size = maximum_page_size
		

	def do_workflow(self, data = None):
		"""
		Make decisions and process the workflow accordingly
		"""
		
		# Quick test for nextPageToken
		self.handle_nextPageToken()

		# Schedule an activity
		if(self.token != None):
			if(self.activity_status(self.decision, activityType = "PingWorker") == False):
				activity_id='PingWorker.ActivityTask.' + self.get_time() + '.%s' % int(random.random() * 10000)
				activity_type = 'PingWorker'

				self.logger.info('scheduling task: %s' % activity_id)
				d = Layer1Decisions()
				d.schedule_activity_task(activity_id,           # Activity ID
																 activity_type,         # Activity Type
																 '1',                   # Activity Type Version
																 self.settings.default_task_list,                  # Task List(use default)
																 'control data',        # control
																 '300',                 # Heartbeat in seconds
																 '300',                 # schedule_to_close_timeout
																 '300',                 # schedule_to_start_timeout
																 '300',                  # start_to_close_timeout
																 json.dumps(data))    # input: extra data to pass to activity
				
				#------------------------------------------------------------------
				# Complete Decision Task
				#  - easy enough
				if(d is None):
					d = Layer1Decisions()
				out = self.conn.respond_decision_task_completed(self.token,d._data)
				self.logger.info('respond_decision_task_completed returned %s' % out)
				#------------------------------------------------------------------
			
			elif(self.activity_status(self.decision, activityType = "ArticleToFluidinfo") == False):
				activity_id='ArticleToFluidinfo.ActivityTask.' + self.get_time() + '.%s' % int(random.random() * 10000)
				activity_type = 'ArticleToFluidinfo'

				self.logger.info('scheduling task: %s' % activity_id)
				d = Layer1Decisions()
				d.schedule_activity_task(activity_id,           # Activity ID
																 activity_type,         # Activity Type
																 '1',                   # Activity Type Version
																 self.settings.default_task_list,                  # Task List(use default)
																 'control data',        # control
																 '300',                 # Heartbeat in seconds
																 '300',                 # schedule_to_close_timeout
																 '300',                 # schedule_to_start_timeout
																 '300',                  # start_to_close_timeout
																 json.dumps(data))    # input: extra data to pass to activity
				
				#------------------------------------------------------------------
				# Complete Decision Task
				#  - easy enough
				if(d is None):
					d = Layer1Decisions()
				out = self.conn.respond_decision_task_completed(self.token,d._data)
				self.logger.info('respond_decision_task_completed returned %s' % out)
				#------------------------------------------------------------------
				
			
			else:
				# Complete the workflow execution
				d = Layer1Decisions()
				d.complete_workflow_execution()
				out = self.conn.respond_decision_task_completed(self.token,d._data)
				self.logger.info('respond_decision_task_completed returned %s' % out)
		
		return True