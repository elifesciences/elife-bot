import boto.swf
import json
import random
import datetime
import importlib
import os
import zipfile

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
		
		# Activity specific properties
		self.document = None
		self.content = None
		self.a = None
		
		# Where we specify the library to be imported
		self.elife_api_prototype = None
		
		# Import the libraries we will need
		self.import_imports()
	
	def do_activity(self, data = None):
		"""
		ArticleToFluidinfo activity, do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		# Set the document path
		document = '../elife-api-prototype/sample-xml/' + data["data"]["document"]

		# Read in the document and write it to the temp directory
		self.read_document_to_content(document)
		self.write_content_to_document(data["data"]["document"])

		self.parse_document(self.document)
		
		result = None
		if(self.a is not None):
			result = self.load_article()

		return result
	
	def read_document_to_content(self, document):
		mode = "r"
		
		if(self.is_zip(document)):
			document = self.unzip_document(document)
			self.document = document
		
		f = open(document, mode)
		self.content = f.read()
		f.close()

	def write_content_to_document(self, filename):
		mode = "w"
		
		f = self.open_file_from_tmp_dir(filename, mode)
		f.write(self.content)
		f.close()
		
		# Reset the object document
		tmp_dir = self.get_tmp_dir()
		if(tmp_dir):
			self.document = tmp_dir + os.sep + filename
		else:
			self.document = filename
			
	def is_zip(self, document):
		"""
		Given a document name, determine if it a zip file
		"""
		fileName, fileExtension = os.path.splitext(document)
		if(fileExtension == ".zip"):
			return True
		return False
		
	def unzip_document(self, document):
		"""
		Unzip the document if it is a zip,
		and return the XML document name
		"""
		mode = "r"
		tmp_dir = self.get_tmp_dir()
		
		z = zipfile.ZipFile(document)

		xml_filename = None
		for f in z.namelist():
			z.extract(f, tmp_dir)
			xml_filename = f
		z.close()
		
		# Only handles one file at a time, for now
		if(tmp_dir):
			document = tmp_dir + os.sep + xml_filename
		else:
			document = xml_filename
		
		return document

	def get_document(self):
		"""
		Return the object document name
		"""
		return self.document

	def parse_document(self, document):
		"""
		Parse the XML document into an article object
		"""

		self.document = document
		
		path = None

		# Article class from the library
		article = self.elife_api_prototype.article

		# Can now specify to the article object our objects explicitly
		self.a = article.article()
		self.a.parse_document(path, self.document)
				
	def load_article(self):
		"""
		Customised load article function in order to override
		the Fluidinfo namespace used by the default parseFI parser
		MUST load settings module first, override the values (i.e. the namespace)
		BEFORE loading anything else, or the override will not take effect
		"""
		if(self.a is None):
			return False

		load_article = self.elife_api_prototype.load_article

		#print json.dumps(load_article.settings.namespace, sort_keys=True, indent=4)
		
		load_article.load_article_into_fi(self.a)
		return True

	def import_imports(self):
		"""
		Customised importing of the elife-api-prototype library
		to override the Fluidinfo namespace used by the default parseFI parser
		MUST load settings module first, override the values (i.e. the namespace)
		BEFORE loading anything else, or the override will not take effect
		"""
		
		# Load the API prototype files from parent directory - hellish imports but they
		#  seem to work now
		
		self.elife_api_prototype = __import__("elife-api-prototype")
		# Load external library settings
		importlib.import_module("elife-api-prototype.settings")
		settings = self.elife_api_prototype.settings
		# Override the namespace
		settings.namespace = self.settings.fi_namespace

		# Now we can continue with imports
		importlib.import_module("elife-api-prototype.article")
		importlib.import_module("elife-api-prototype.load_article")
