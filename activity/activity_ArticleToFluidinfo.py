import boto.swf
import json
import random
import datetime
import importlib

import activity

"""
ArticleToFluidinfo activity
"""

class activity_ArticleToFluidinfo(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "ArticleToFluidinfo"
		self.version = "1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*10
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = "Publish article to Fluidinfo"
	
	def do_activity(self, data = None):
		"""
		ArticleToFluidinfo activity, do the work
		"""
		self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		# Set the document path
		document = '../elife-api-prototype/sample-xml/' + data["data"]["document"]

		result = self.load_article(document)

		return result
	
	def load_article(self, document):
		"""
		Customised load article function in order to override
		the Fluidinfo namespace used by the default parseFI parser
		MUST load settings module first, override the values (i.e. the namespace)
		BEFORE loading anything else, or the override will not take effect
		"""
		doi = None
		path = None

		# Load the API prototype files from parent directory - hellish imports but they
		#  seem to work now

		elife_api_prototype = __import__("elife-api-prototype")
		# Load external library settings
		importlib.import_module("elife-api-prototype.settings")
		settings = elife_api_prototype.settings
		# Override the namespace
		settings.namespace = self.settings.fi_namespace

		# Now we can continue with imports
		importlib.import_module("elife-api-prototype.article")
		importlib.import_module("elife-api-prototype.load_article")
		article = elife_api_prototype.article
		load_article = elife_api_prototype.load_article
		
		# Can now specify to the article object our objects explicitly
		a = article.article()
		a.parse_document(path, document)
		
		#print json.dumps(load_article.settings.namespace, sort_keys=True, indent=4)
		
		load_article.load_article_into_fi(a)
		return True
