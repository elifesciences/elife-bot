import boto.swf
import json
import random
import datetime
import calendar
import time
import os

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.filesystem as fslib

"""
ArticleToOutbox activity
"""

class activity_ArticleToOutbox(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "ArticleToOutbox"
		self.version = "1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*5
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = "Download a S3 object from the elife-articles bucket, unzip if necessary, and save to outbox folder on S3."
		
		# Create the filesystem provider
		self.fs = fslib.Filesystem(self.get_tmp_dir())
		
		# Bucket for outgoing files
		self.publish_bucket = settings.poa_packaging_bucket
		
		# Folder for pubmed XML
		self.pubmed_outbox_folder = "pubmed/outbox/"
		self.publication_email_outbox_folder = "publication_email/outbox/"
		self.pub_router_outbox_folder = "pub_router/outbox/"
		self.cengage_outbox_folder = "cengage/outbox/"
		self.gooa_outbox_folder = "gooa/outbox/"

	def do_activity(self, data = None):
		"""
		Do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		elife_id = data["data"]["elife_id"]
				
		# Download the S3 object
		document = data["data"]["document"]
		self.fs.write_document_to_tmp_dir(document)
		
		# The document location on local file system
		tmp_document_path = self.get_document()
		# Clean up to get the filename alone
		tmp_document = self.get_document_name_from_path(tmp_document_path)
		
		# 1. Send the file to the pubmed outbox
		self.copy_document_to_outbox(
			path = tmp_document_path,
			document = tmp_document,
			outbox_folder = self.pubmed_outbox_folder)
		
		# 2. Send the file to the publication email outbox
		self.copy_document_to_outbox(
			path = tmp_document_path,
			document = tmp_document,
			outbox_folder = self.publication_email_outbox_folder)
		
		# 3. Send the file to the pub router outbox
		self.copy_document_to_outbox(
			path = tmp_document_path,
			document = tmp_document,
			outbox_folder = self.pub_router_outbox_folder)

		# 4. Send the file to the cengage outbox
		self.copy_document_to_outbox(
			path = tmp_document_path,
			document = tmp_document,
			outbox_folder = self.cengage_outbox_folder)

		# 5. Send the file to the GoOA outbox
		self.copy_document_to_outbox(
			path = tmp_document_path,
			document = tmp_document,
			outbox_folder = self.gooa_outbox_folder)

		if(self.logger):
			self.logger.info('ArticleToOutbox: %s' % elife_id)

		return True
	
	def get_document(self):
		"""
		Exposed for running tests
		"""
		if(self.fs.tmp_dir):
			full_filename = self.fs.tmp_dir + os.sep + self.fs.get_document()
		else:
			full_filename = self.fs.get_document()
		
		return full_filename

	def get_document_name_from_path(self, document_path):
		"""
		Given a document location in the tmp directory
		slice away everything but the filename and return it
		"""
		document = document_path.replace(self.get_tmp_dir(), '')
		document = document.replace("", '')
		document = document.replace("\\", '')
		return document

	def copy_document_to_outbox(self, path, document, outbox_folder):
		"""
		Given the document name and the outbox folder
		On S3 copy the document to the folder
		"""

		# Get an S3 key name for where to save the XML
		delimiter = self.settings.delimiter
		prefix = outbox_folder
		s3key_name = prefix + document
		
		# Create S3 key and save the file there
		bucket_name = self.publish_bucket
		
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
		bucket = s3_conn.lookup(bucket_name)
		
		s3key = boto.s3.key.Key(bucket)
		s3key.key = s3key_name
		s3key.set_contents_from_filename(path, replace=True)