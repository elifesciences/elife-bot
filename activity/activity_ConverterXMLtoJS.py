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
ConverterXMLtoJS activity
"""

class activity_ConverterXMLtoJS(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "ConverterXMLtoJS"
		self.version = "1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*5
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = "PUT XML into the converter, then GET the JSON and JSONP, and then save those to the S3 CDN bucket."
		
		# Create the filesystem provider
		self.fs = fslib.Filesystem(self.get_tmp_dir())

	def do_activity(self, data = None):
		"""
		Do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
		
		elife_id = data["data"]["elife_id"]
		
		url = "https://s3.amazonaws.com/elife-cdn/elife-articles/" + elife_id + "/elife" + elife_id + ".xml"
		token = self.settings.converter_token
		
		headers = {"Content-Type": "application/json"}
		
		data["url"] = url
		data["token"] = token
		
		put_url = self.settings.converter_url + '/documents/' + elife_id
		r = requests.put(put_url, data=json.dumps(data), headers=headers)

		if(r.status_code == requests.codes.ok):
			# Good, now we can do a get request
			
			# Wait briefly for the converter to process the PUT completely
			time.sleep(5)
			
			get_json_url = self.settings.converter_url + '/documents/' + elife_id
			get_jsonp_url = self.settings.converter_url + '/documents/' + elife_id + '?callback=handleDoc'
			
			json_s3key = '/documents/elife/' + elife_id + '.json'
			jsonp_s3key = '/documents/elife/' + elife_id + '.js'
			
			json_filename = elife_id + '.json'
			jsonp_filename = elife_id + '.js'
			
			"""
			print get_json_url
			print get_jsonp_url
			print json_s3key
			print jsonp_s3key
			print json_filename
			print jsonp_filename
			"""
			
			# Save the document to the elife-cdn bucket
			bucket_name = 'elife-cdn'
			# Connect to S3
			s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
			# Lookup bucket
			bucket = s3_conn.lookup(bucket_name)

			# 1. JSON
			document_name = self.fs.download_document(get_json_url, filename=json_filename, validate_url = False)
			# Create S3 key and save the file there
			s3key = boto.s3.key.Key(bucket)
			s3key.key = json_s3key
			s3key.set_contents_from_filename(document_name, replace=True)
			
			if(self.logger):
				self.logger.info('ConverterXMLtoJS: %s' % json_s3key)
			
			# 2. JSONP
			document_name = self.fs.download_document(get_jsonp_url, filename=jsonp_filename, validate_url = False)
			# Create S3 key and save the file there
			s3key = boto.s3.key.Key(bucket)
			s3key.key = jsonp_s3key
			s3key.set_contents_from_filename(document_name, replace=True)
			
			if(self.logger):
				self.logger.info('ConverterXMLtoJS: %s' % jsonp_s3key)

		else:
			return False
		
		return True
