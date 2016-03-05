import boto.swf
from boto.swf.layer1_decisions import Layer1Decisions
import json
import random
import datetime

import workflow

"""
LensArticlePublish workflow
"""

class workflow_LensArticlePublish(workflow.workflow):
	
	def __init__(self, settings, logger, conn = None, token = None, decision = None, maximum_page_size = 100, definition = None):
		workflow.workflow.__init__(self, settings, logger, conn, token, decision, maximum_page_size)

		# SWF Defaults
		self.name = "LensArticlePublish"
		self.version = "1"
		self.description = "Publish an article to eLife Lens CDN."
		self.default_execution_start_to_close_timeout = 60*10
		self.default_task_start_to_close_timeout = 30
		
		# Get the input from the JSON decision response
		data = self.get_input()
		
		# JSON format workflow definition, for now
		workflow_definition = {
			"name": "LensArticlePublish",
			"version": "1",
			"task_list": self.settings.default_task_list,
			"input": data,
	
			"start":
			{
				"requirements": None
			},
			
			"steps":
			[
				{
					"activity_type": "PingWorker",
					"activity_id": "PingWorker",
					"version": "1",
					"input": data,
					"control": None,
					"heartbeat_timeout": 300,
					"schedule_to_close_timeout": 300,
					"schedule_to_start_timeout": 300,
					"start_to_close_timeout": 300
				},
				{
					"activity_type": "LensArticle",
					"activity_id": "LensArticle",
					"version": "1",
					"input": data,
					"control": None,
					"heartbeat_timeout": 60*5,
					"schedule_to_close_timeout": 60*5,
					"schedule_to_start_timeout": 300,
					"start_to_close_timeout": 60*5
				}
			],
		
			"finish":
			{
				"requirements": None
			}
		}
		
		self.load_definition(workflow_definition)
		