import os
# Add parent directory for imports, so activity classes can use elife-api-prototype
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
from optparse import OptionParser

import provider.simpleDB as dblib

"""
Amazon SWF PublishSVG starter
"""

class starter_PublishSVG():

	def start(self, ENV = "dev", all = None, last_updated_since = None, docs = None, doi_id = None):
		# Specify run environment settings
		settings = settingsLib.get_settings(ENV)
		
		# Log
		identity = "starter_%s" % int(random.random() * 1000)
		logFile = "starter.log"
		#logFile = None
		logger = log.logger(logFile, settings.setLevel, identity)
		
		# Simple connect
		conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
	
		if(all == True):
			# Publish all articles, use SimpleDB as the source
			docs = self.get_docs_from_SimpleDB(ENV)
	
		elif(doi_id is not None):
			docs = self.get_docs_from_SimpleDB(ENV, doi_id = doi_id)
			
		elif(last_updated_since is not None):
			# Publish only articles since the last_modified date, use SimpleDB as the source
			docs = self.get_docs_from_SimpleDB(ENV, last_updated_since = last_updated_since)

		if(docs):
			for doc in docs:
				
				document = doc["document"]
				elife_id = doc["elife_id"]
		
				id_string = elife_id
		
				# Start a workflow execution
				workflow_id = "PublishSVG_%s" % (id_string)
				workflow_name = "PublishSVG"
				workflow_version = "1"
				child_policy = None
				execution_start_to_close_timeout = str(60*15)
				input = '{"data": ' + json.dumps(doc) + '}'
		
				try:
					response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)
		
					logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
					
				except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
					# There is already a running workflow with that ID, cannot start another
					message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
					print message
					logger.info(message)

	def get_docs_from_SimpleDB(self, ENV = "dev", last_updated_since = None, doi_id = None):
		"""
		Get the array of docs from the SimpleDB provider
		"""
		docs = []
		
		# Specify run environment settings
		settings = settingsLib.get_settings(ENV)
		
		db = dblib.SimpleDB(settings)
		db.connect()
		
		if(last_updated_since is not None):
			xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "svg", latest = True, last_updated_since = last_updated_since)
		elif(doi_id is not None):
			xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "svg", latest = True, doi_id = doi_id)
		else:
			# Get all
			xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "svg", latest = True)
			
		for x in xml_item_list:
			tmp = {}
			elife_id = str(x['name']).split("/")[0]
			document = 'https://s3.amazonaws.com/' + x['item_name']
			tmp['elife_id'] = elife_id
			tmp['document'] = document
			docs.append(tmp)
		
		return docs

if __name__ == "__main__":

	doi_id = None
	last_updated_since = None
	all = False
	
	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	parser.add_option("-u", "--last-updated-since", default=None, action="store", type="string", dest="last_updated_since", help="specify the datetime for last_updated_since")
	parser.add_option("-d", "--doi-id", default=None, action="store", type="string", dest="doi_id", help="specify the DOI id of a single article")
	parser.add_option("-a", "--all", default=None, action="store_true", dest="all", help="start workflow for all files")
	
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env
	if options.last_updated_since:
		last_updated_since = options.last_updated_since
	if options.doi_id:
		doi_id = options.doi_id
	if options.all:
		all = options.all

	o = starter_PublishSVG()

	o.start(ENV, last_updated_since = last_updated_since, all = all, doi_id = doi_id)