import boto.swf
import json
import random
import datetime
import os

"""
Amazon SWF activity base class
"""

class activity(object):
	# Base class
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		self.settings = settings
		self.logger = logger
		self.result = None
		self.conn = conn
		self.token = token
		self.activity_task = activity_task
		
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
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*10
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*5
		self.description = None
		
		self.tmp_dir = "tmp"

	def describe(self):
		"""
		Describe activity type from SWF, to confirm it exists
		Requires object to have an active connection to SWF using boto
		"""
		if(self.conn == None or self.domain == None or self.name == None or self.version == None):
			return None
		
		try:
			response = self.conn.describe_activity_type(self.domain, self.name, self.version)
		except boto.exception.SWFResponseError:
			response = None
		
		return response
	
	def register(self):
		"""
		Register the activity type with SWF, if it does not already exist
		Requires object to have an active connection to SWF using boto
		"""
		if(self.conn == None or self.domain == None or self.name == None or self.version == None):
			return None
		
		if(self.describe() is None):
			response = self.conn.register_activity_type(
				str(self.domain),
				str(self.name),
				str(self.version),
				str(self.task_list),
				str(self.default_task_heartbeat_timeout),
				str(self.default_task_schedule_to_close_timeout),
				str(self.default_task_schedule_to_start_timeout),
				str(self.default_task_start_to_close_timeout),
				str(self.description))
			
			return response

	def open_file_from_tmp_dir(self, filename, mode = 'r'):
		"""
		Read the file from the tmp_dir
		"""
		# Try and make the directory, if it does not exist
		try:
			os.mkdir(self.tmp_dir)
		except OSError:
			pass
		
		full_filename = self.tmp_dir + os.sep + filename
		f = open(full_filename, mode)
		return f
		