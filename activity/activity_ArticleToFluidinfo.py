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
	
	def do_activity(self, data = None):
		"""
		ArticleToFluidinfo activity, do the work
		"""
		self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		# Load the API prototype files from parent directory - hellish imports but they
		#  seem to work now
		elife_api_prototype = __import__("elife-api-prototype")
		importlib.import_module("elife-api-prototype.load_article")

		# Set the document path
		document = '../elife-api-prototype/sample-xml/' + data["data"]["document"]
		load_article = elife_api_prototype.load_article

		# Failsafe, set the fluidinfo namespace to dev while under development
		#  !!!!!! Do not seem to work atm !!!!!!!!!!
		settings = elife_api_prototype.settings
		settings.namespace = 'elifesciences.org/api_dev'
		
		article = load_article.load_article(document)
		load_article.load_article_into_fi(article)

		#print json.dumps(article.data(), sort_keys=True, indent=4)
		
		return True
