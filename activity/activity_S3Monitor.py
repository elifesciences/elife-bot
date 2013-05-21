import boto.swf
import json
import random
import datetime
import calendar
import time

import activity

import boto.sdb
import boto.s3
from boto.s3.connection import S3Connection

"""
S3Monitor activity
"""

class activity_S3Monitor(activity.activity):
	
	def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
		activity.activity.__init__(self, settings, logger, conn, token, activity_task)

		self.name = "S3Monitor"
		self.version = "1.1"
		self.default_task_heartbeat_timeout = 30
		self.default_task_schedule_to_close_timeout = 60*15
		self.default_task_schedule_to_start_timeout = 30
		self.default_task_start_to_close_timeout= 60*15
		self.description = "S3Monitor activity: poll S3 bucket and save object metadata into SimpleDB."
	
	def do_activity(self, data = None):
		"""
		S3Monitor activity, do the work
		"""
		if(self.logger):
			self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
			
		bucket_name = self.settings.bucket
		prefix = self.settings.prefix
		delimiter = self.settings.delimiter
		
		# Set the current time for this run, to help discover deleted files
		_runtime_timestamp = calendar.timegm(time.gmtime())
		
		# Connect to SimpleDB
		sdb_conn = self.connect_to_sdb(self.settings.simpledb_region, self.settings.aws_access_key_id, self.settings.aws_secret_access_key)

		# Check the SimpleDB domain exists and get it
		dom_S3File = self.sdb_get_domain(sdb_conn, self.settings.simpledb_S3File_domain)
		dom_S3FileLog = self.sdb_get_domain(sdb_conn, self.settings.simpledb_S3FileLog_domain)

		# Connect to S3
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
	
		# Lookup bucket
		bucket = s3_conn.lookup(bucket_name)

		(keys, folders) = self.get_keys_and_folders(bucket, prefix)

		self.sdb_update_keys_and_folder_items(dom_S3File, dom_S3FileLog, keys, folders, bucket_name, _runtime_timestamp, prefix, delimiter)
				
		# Map one more level of directories - a quick hack before parallel execution
		(keys, folders) = self.get_keys_and_folders(bucket, prefix)
		for folder in folders:
			prefix = folder.name
			(keys2, folders2) = self.get_keys_and_folders(bucket, prefix)
			self.sdb_update_keys_and_folder_items(dom_S3File, dom_S3FileLog, keys2, folders2, bucket_name, _runtime_timestamp, prefix, delimiter)

		return True

	def connect_to_sdb(self, region = "us-east-1", aws_access_key_id = None, aws_secret_access_key = None):
		return boto.sdb.connect_to_region(region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
		
	def sdb_domain_exists(self, sdb_conn, domain_name):
		exists = None
		try:
			dom = sdb_conn.get_domain(domain_name, validate = True)
			if(dom):
				exists = True
		except boto.exception.SDBResponseError:
			exists = False
		return exists

	def sdb_create_domain(self, sdb_conn, domain_name):
		dom = sdb_conn.create_domain(domain_name)
		return dom
	
	def sdb_get_domain(self, sdb_conn, domain_name, auto_create_domain = True):
		"""
		Get the SimpleDB domain, and optionally create it if is does not yet exist
		"""
		dom = None
		try:
			dom = sdb_conn.get_domain(domain_name)
		except boto.exception.SDBResponseError:
			# Domain did not exist, create if we specified to
			if(auto_create_domain):
				if(self.sdb_domain_exists(sdb_conn, domain_name) == False):
					dom = self.sdb_create_domain(sdb_conn, domain_name)
			else:
				dom = None
				
		return dom
	
	def sdb_update_keys_and_folder_items(self, dom_S3File, dom_S3FileLog, keys, folders, bucket_name, _runtime_timestamp = None, prefix = '', delimiter = '/'):
		"""
		Given the attributes for keys or folders from S3, update the SimpleDB domain
		items with the supplied values. Each attribute of a SimpleDB item will be overwritten, not
		appended to a list, in this function.
		Existing attributes for the item are not deleted.
		"""
		
		item_attrs = {}
		item_attrs['bucket_name'] = bucket_name
		
		# Logging the activity runtime
		if(_runtime_timestamp):
			item_attrs['_runtime_timestamp'] = _runtime_timestamp
			time_tuple = time.gmtime(_runtime_timestamp)
			item_attrs['_runtime_date'] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time_tuple)
			item_attrs['_runtime_year'] = time.strftime("%Y", time_tuple)
			item_attrs['_runtime_month'] = time.strftime("%m", time_tuple)
			item_attrs['_runtime_day'] = time.strftime("%d", time_tuple)
			item_attrs['_runtime_time'] = time.strftime("%H:%M:%S", time_tuple)
		
		for folder in folders:
			item_name = bucket_name + delimiter + folder.name
			#print item_name
			item = dom_S3File.get_item(item_name, consistent_read=True)
			
			item_attrs['item_name'] = item_name

			if(item is None):
				# Create the item
				dom_S3File.put_attributes(item_name, item_attrs)
			else:
				# Update the item attributes by replacing values if present
				for k, v in item_attrs.items():
					if(item.has_key(k)):
						# Overwrite value
						item[k] = v
					else:
						# Create the new attribute
						item.add_value(k, v)
				item.save()
				
		for key in keys:
			item_name = bucket_name + delimiter + key.name
			#print item_name
			item = dom_S3File.get_item(item_name, consistent_read=True)
			
			item_attrs['item_name'] = item_name
			
			# Standard attributes returned from a standard boto list call
			attr_list = ['name','content_type',
									 'etag','last_modified',
									 'owner','storage_class',
									 'size']
			# Extended attributes, not used yet
			#  'metadata','cache_control','content_encoding','content_disposition',
			#  'content_language','md5','version_id','encrypted'

			for attr_name in attr_list:
				# Reading values from keys
				#  Ignore None values, but convert others to string first
				#  for simplicity
				raw_value = eval("key." + attr_name)
				if(raw_value):
					string_value = str(raw_value)
					item_attrs[attr_name] = string_value
					#print attr_name + ' = ' + item_attrs[attr_name]
				
			# Extended last_modified values
			# Example format: 2013-01-26T23:48:28.000Z
			if(item_attrs['last_modified']):
				date_string = time.strptime(item_attrs['last_modified'], "%Y-%m-%dT%H:%M:%S.000Z")
				last_modified_timestamp = calendar.timegm(date_string)
				item_attrs['last_modified_timestamp'] = last_modified_timestamp
				time_tuple = time.gmtime(last_modified_timestamp)
				item_attrs['last_modified_year'] = time.strftime("%Y", time_tuple)
				item_attrs['last_modified_month'] = time.strftime("%m", time_tuple)
				item_attrs['last_modified_day'] = time.strftime("%d", time_tuple)
				item_attrs['last_modified_time'] = time.strftime("%H:%M:%S", time_tuple)

			if(item is None):
				# Create the item
				dom_S3File.put_attributes(item_name, item_attrs)
				# Add to the item log
				self.sdb_log_item_modified(item_name, item_attrs, dom_S3FileLog)
			else:
				# Log the details if it has been modifed
				if(self.item_diff(item, item_name, item_attrs, dom_S3FileLog)):
					self.sdb_log_item_modified(item_name, item_attrs, dom_S3FileLog)
				
				# Update the item attributes by replacing values if present
				for k, v in item_attrs.items():
					if(item.has_key(k)):
						# Overwrite value
						item[k] = v
					else:
						# Create the new attribute
						item.add_value(k, v)
				item.save()
				
	def get_log_item_name(self, item_name, item_attrs):
		"""
		Given an item name and its attributes, return what the resulting
		unique log item name would be
		"""
		log_item_name = None
		try:
			log_item_name = str(item_attrs['last_modified_timestamp']) + '_' + item_name
		except IndexError:
			log_item_name = '0' + '_' + item_name
			
		return log_item_name
		
	def item_diff(self, item, item_name, item_attrs, dom_S3FileLog):
		"""
		Given an SDB item and some attributes, check for the most recent item
		in the SDB log. If it is unchanged since the last time we looked at it
		return False; if it has changed or the item does not appear in the log,
		return true
		"""
		diff = False
		
		log_item_name = self.get_log_item_name(item_name, item_attrs)
		
		log_item = dom_S3FileLog.get_item(log_item_name, consistent_read=True)
		if(log_item is None):
			diff = True
		else:
			# Got a log item, compare attributes to determine whether it is modified
			if(item['name'] == log_item['name'] and
				 item['last_modified_timestamp'] != item_attrs['last_modified_timestamp']):
				diff = True
		
		return diff
				
	def sdb_log_item_modified(self, item_name, item_attrs, dom_S3FileLog):
		"""
		After detecting a new or modified S3 object, add a new item to the
		S3FileLog domain. Each item needs a unique key. If an item already exists
		for the unique key, there's no need to modify it
		"""

		log_item_name = self.get_log_item_name(item_name, item_attrs)

		item_attrs['log_item_name'] = log_item_name
		
		# Check if it already exists
		log_item = dom_S3FileLog.get_item(log_item_name, consistent_read=True)
		if(log_item is None):
			dom_S3FileLog.put_attributes(log_item_name, item_attrs)


	def get_keys_and_folders(self, bucket, prefix = None, delimiter = '/', headers = None):
		# Get "keys" and "folders" from the bucket, with optional
		# prefix for the "folder" of interest
		# default delimiter is '/'
		
		if(bucket is None):
			return None
	
		folders = []
		keys = []
	
		bucketList = bucket.list(prefix = prefix, delimiter = delimiter, headers = headers)
	
		for item in bucketList:
			if(isinstance(item, boto.s3.prefix.Prefix)):
				# Can loop through each prefix and search for objects
				folders.append(item)
				#print 'Prefix: ' + item.name
			elif (isinstance(item, boto.s3.key.Key)):
				keys.append(item)
				#print 'Key: ' + item.name
	
		return keys, folders

