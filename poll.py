import boto
from boto.s3.connection import S3Connection
import settings as settingsLib
import json
import datetime

"""
Polling s3 buckets and objects
"""

def main(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Simple S3 connect
	conn = S3Connection(settings.aws_access_key_id, settings.aws_secret_access_key)

	# Lookup bucket
	bucket = conn.lookup(settings.bucket)
	
	# Get folders in the root of bucket
	(keys, folders) = get_folders(bucket)
	#debug_print(keys)
	#debug_print(folders)
	
	"""
	# Perform actions on non-folder items
	for item in keys:
		print item.name
		print item.last_modified
		for key,value in item.metadata:
			print key + ',' + value
		print item.version_id
		print item.metadata
		#item.set_metadata('test', 'value')
	"""
	
	# Get the folders from base folder specified by prefix
	(keys, folders) = get_folders(bucket, prefix = settings.prefix, delimiter = settings.delimiter)
	#debug_print(keys)
	#debug_print(folders)

	for folder in folders:
		(keys, folders) = get_folders(bucket, folder.name, delimiter = settings.delimiter)
		# Debug print all keys found
		#debug_print(keys)
		
		# Super new test, print only those with date modified after
		for key in keys:
			if(datetime.datetime.strptime(key.last_modified, '%Y-%m-%dT%H:%M:%S.000Z') > datetime.datetime.strptime('2013-01-15T12:59:45.000Z', '%Y-%m-%dT%H:%M:%S.000Z')):
				print key.name
		

		
	
	"""
	for key in keys:
		# Do a separate head request on the key to get full metadata
		keyItem = bucket.get_key(key.name)
		debug_print([keyItem])
	"""
		
	"""
	# For each folder, do something
	for folder in folders:
		# Do a HEAD request on the key, to get metadata
		key = bucket.get_key(folder.name)
		print key.name
		print key.last_modified
		print key.content_type
		print key.metadata

		# Set metadata, seems you can only do this by copying, to the same bucket
		#add_meta(bucket, key, metadata = {'published': 'true'})
		#clear_meta(bucket, key)
	"""
	
	"""
	for folder in folders:
		(keys, folders) = get_folders(bucket, prefix = folder.name, delimiter = settings.delimiter)
		for item in keys:
			# Do a HEAD request on the key, to get metadata
			key = bucket.get_key(item.name)
			print key.name
			print key.last_modified
			print key.content_type
			print key.metadata
			add_meta(bucket, key, metadata = {'published': 'true'})
			add_meta(bucket, key, metadata = {'published_date': '2012-12-05 00:48:10'})
			add_meta(bucket, key, metadata = {'doi': '10.7554/elife.00013'})
			#item.set_metadata('test', 'value')
	"""

	"""
	# For each folder, get all keys in the folder from the bucket
	for folder in folders:
		(keys, folders) = get_folders(bucket, prefix = settings.prefix, delimiter = settings.delimiter)
		#print folder.name
		for item in keys:
			# Do a HEAD request on the key, to get metadata
			#headers = {'If-Modified-Since': '2010-01-01'}
			keyItem = bucket.get_key(item.name)
			print keyItem.name
			print keyItem.last_modified
			print keyItem.content_type
			print keyItem.metadata
			#keyItem.set_metadata('test', 'value')
			#keyItem.update_metadata({'Test': 'value'})
			# Set metadata, seems you can only do this by copying, to the same bucket
			add_meta(bucket, keyItem, metadata = {'Test2': 'value'})
			#keyItem.copy(bucket, keyItem.name, preserve_acl=True, metadata=)
			#keyItem.set_remote_metadata({'test': 'value'})
			#print keyItem.get_metadata('Test-Inside')
		"""
	"""
	for key in keys:
		# Copy the key onto itself, preserving the ACL but changing the content-type

		print key.name
		keyItem = bucket.get_key(key.name)
		print keyItem.content_type
	"""
	

def get_folders(bucket, prefix = None, delimiter = '/', headers = None):
	# Get "folders" from the bucket, with optional
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

def add_meta(bucket, key, metadata):
	"""
	Add metadata value remotely by copying the key (object) to the same bucket
	and adding metadata (dict) at the same time, preserving existing metadata
	"""
	meta = key.metadata
	for k,v in metadata.items():
		k = k.lower()
		meta[k] = v
	key.copy(bucket, key.name, preserve_acl=True, metadata = meta)
	return meta

def clear_meta(bucket, key):
	"""
	Clear all metadata on the key object
	"""
	meta = {}
	key.copy(bucket, key.name, preserve_acl=True, metadata = meta)
	return meta

def debug_print(obj):
	for o in obj:
		if(isinstance(o, boto.s3.prefix.Prefix)):
			print 'Prefix: ' + o.name
		elif (isinstance(o, boto.s3.key.Key)):
			print '\nKey: ' + o.name
			print '  bucket: ' + str(o.bucket or '')
			print '  name: ' + str(o.name or '')
			print '  metadata: ' + str(o.metadata or '')
			print '  cache_control: ' + str(o.cache_control or '')
			print '  content_type: ' + str(o.content_type or '')
			print '  content_encoding: ' + str(o.content_encoding or '')
			print '  content_disposition: ' + str(o.content_disposition or '')
			print '  content_language: ' + str(o.content_language or '')
			print '  etag: ' + str(o.etag or '')
			print '  last_modified: ' + str(o.last_modified or '')
			print '  owner: ' + str(o.owner or '')
			print '  storage_class: ' + str(o.storage_class or '')
			print '  md5: ' + str(o.md5 or '')
			print '  size: ' + str(o.size or '')
			print '  version_id: ' + str(o.version_id or '')
			print '  encrypted: ' + str(o.encrypted or '')


# Get all buckets test
#rs = conn.get_all_buckets()
#print len(rs)
#for b in rs:
#	print b.name

if __name__ == "__main__":
	main()