import boto.swf
import json
import random
import datetime
import calendar
import time
import requests
import os

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib

"""
LensArticle activity
"""

class activity_LensArticle(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "LensArticle"
		self.version = "1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*5
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = "Create a lens article index.html page for the particular article."
		
		# Create the filesystem provider
		self.fs = fslib.Filesystem(self.get_tmp_dir())

	def do_activity(self, data = None):
		"""
		Do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		# Temporary use of local header and footer files
		self.header_html_file = "template/lens_article_header.html"
		self.footer_html_file = "template/lens_article_footer.html"
		
		elife_id = data["data"]["elife_id"]
		
		xml_file_url = self.get_xml_file_url(elife_id)
		
		article_s3key = self.get_article_s3key(elife_id)
		
		filename = "index.html"
		
		article_html = self.get_article_html(xml_file_url)
		
		# Write the document to disk first
		self.fs.write_content_to_document(article_html, filename)
		
		# Now, set the S3 object to the contents of the filename
		# Connect to S3
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
		# Lookup bucket
		bucket_name = self.settings.lens_bucket
		bucket = s3_conn.lookup(bucket_name)
		s3key = boto.s3.key.Key(bucket)
		s3key.key = article_s3key
		s3key.set_contents_from_filename(self.get_document(), replace=True)
		
		if(self.logger):
			self.logger.info('LensArticle created for: %s' % article_s3key)

		return True
	
	def get_xml_file_url(self, elife_id):
		"""
		Given an eLife article DOI ID (5 digits) assemble the
		URL of where it is found
		"""
		xml_url = "https://s3.amazonaws.com/" + self.settings.cdn_bucket + "/elife-articles/" + elife_id + "/elife" + elife_id + ".xml"
		
		return xml_url
	
	def get_article_s3key(self, elife_id):
		"""
		Given an eLife article DOI ID (5 digits) assemble the
		S3 key name for where to save the article index.html page
		"""
		article_s3key = "/" + elife_id + "/index.html"
		
		return article_s3key
		
	def get_header_html(self):
		f = open(self.header_html_file, "rb")
		content = f.read()
		f.close()
		return content
	
	def get_footer_html(self):
		f = open(self.footer_html_file, "rb")
		content = f.read()
		f.close()
		return content
		
	def get_article_html(self, xml_file_url):
		"""
		Given the URL of the article XML file, create a lens article index.html page
		using header, footer or template, as required
		"""
		
		header_html = self.get_header_html()
		footer_html = self.get_footer_html()
		
		document_url_html = "\n" + '        document_url: "' + xml_file_url + '"' + "\n"
		
		article_html = header_html + document_url_html + footer_html

		return article_html
		
	def get_document(self):
		"""
		Exposed for running tests
		"""
		if(self.fs.tmp_dir):
			full_filename = self.fs.tmp_dir + os.sep + self.fs.get_document()
		else:
			full_filename = self.fs.get_document()
		
		return full_filename
