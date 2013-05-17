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
		
		# Connect to SimpleDB
		sdb_conn = self.connect_to_sdb(self.settings.simpledb_region, self.settings.aws_access_key_id, self.settings.aws_secret_access_key)

		# Check the SimpleDB domain exists and get it
		domain_exists = self.sdb_domain_exists(sdb_conn, self.settings.simpledb_S3File_domain)
		dom = None
		if(domain_exists == False):
			dom = self.sdb_create_domain(sdb_conn, self.settings.simpledb_S3File_domain)
			domain_exists = self.sdb_domain_exists(sdb_conn, self.settings.simpledb_S3File_domain)
		else:
			dom = self.sdb_get_domain(sdb_conn, self.settings.simpledb_S3File_domain)

		# Connect to S3
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
	
		# Lookup bucket
		bucket = s3_conn.lookup(bucket_name)

		(keys, folders) = self.get_keys_and_folders(bucket, prefix)

		self.sdb_update_keys_and_folder_items(dom, keys, folders, bucket_name, prefix, delimiter)
				
		# Map one more level of directories - a quick hack before parallel execution
		(keys, folders) = self.get_keys_and_folders(bucket, prefix)
		for folder in folders:
			prefix = folder.name
			(keys2, folders2) = self.get_keys_and_folders(bucket, prefix)
			self.sdb_update_keys_and_folder_items(dom, keys2, folders2, bucket_name, prefix, delimiter)

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
	
	def sdb_get_domain(self, sdb_conn, domain_name):
		dom = sdb_conn.get_domain(domain_name)
		return dom
	
	def sdb_update_keys_and_folder_items(self, dom, keys, folders, bucket_name, prefix = '', delimiter = '/'):
		"""
		Given the attributes for keys or folders from S3, update the SimpleDB domain
		items with the supplied values. Each attribute of a SimpleDB item will be overwritten, not
		appended to a list, in this function.
		Existing attributes for the item are not deleted.
		"""
		
		item_attrs = {}
		item_attrs['bucket_name'] = bucket_name
		
		for folder in folders:
			item_name = bucket_name + delimiter + folder.name
			#print item_name
			item = dom.get_item(item_name, consistent_read=True)
			
			item_attrs['item_name'] = item_name

			if(item is None):
				# Create the item
				dom.put_attributes(item_name, item_attrs)
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
			item = dom.get_item(item_name, consistent_read=True)
			
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

			if(item is None):
				# Create the item
				dom.put_attributes(item_name, item_attrs)
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

