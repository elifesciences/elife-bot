import json
import random
import datetime
import calendar
import time
from operator import itemgetter, attrgetter

import boto.sdb

"""
SimpleDB S3 data provider
A home for SimpleDB functions so code is not duplicated
"""

class SimpleDB(object):
	
	def __init__(self, settings):
		self.settings = settings
		
		self.domain_names = {}
		domain_postfix = ""
		if(self.settings.simpledb_domain_postfix):
			domain_postfix = self.settings.simpledb_domain_postfix
		# Set the names of domains = tables in SimpleDB for our data provider
		self.domain_names['S3File'] = "S3File" + domain_postfix
		self.domain_names['S3FileLog'] = "S3FileLog" + domain_postfix
		
		# Actual domain connections (boto objects), save them for future use once gotten
		self.domains = {}
		
		self.sdb_conn = None
		
		
	def connect(self):
		if(self.settings.simpledb_region):
			region = self.settings.simpledb_region
		else:
			region = "us-east-1"
		self.sdb_conn = self.connect_to_sdb(region, self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
		return self.sdb_conn
		
	def get_item(self, domain_name, item_name, consistent_read=True):
		"""
		Encapsulate boto.sdb get_item, by additionally specifying the domain to read from
		"""
		try:
			self.is_domain(domain_name)
		except:
			pass
		
		dom = self.domains[domain_name]
		return dom.get_item(item_name, consistent_read)
		
	def put_attributes(self, domain_name, item_name, item_attrs):
		"""
		Encapsulate boto.sdb put_attributes, by additionally specifying the domain to put into
		"""
		try:
			self.is_domain(domain_name)
		except:
			pass
		
		dom = self.domains[domain_name]
		dom.put_attributes(item_name, item_attrs)
		
	def is_domain(self, domain_name):
		"""
		Given a domain name, check if the domain is connected,
		and if not, connect to it
		"""
		try:
			if(not self.domains[domain_name]):
				self.sdb_get_domain(domain_name)
		except KeyError:
			self.sdb_get_domain(domain_name)
		
	def get_domain_name(self, domain_name):
		"""
		Given a domain identifier, return the name of the domain (table)
		used at SimpleDB for the particular settings environment
		"""
		try:
			return self.domain_names[domain_name]
		except IndexError:
			return None
		
	def get_domain(self, domain_name):
		"""
		Given a domain name, return the domain
		"""
		domain = None
		try:
			self.is_domain(domain_name)
		except:
			pass
		
		try:
			domain = self.domains[domain_name]
		except:
			pass
		
		return domain
		
	def connect_to_sdb(self, region = "us-east-1", aws_access_key_id = None, aws_secret_access_key = None):
		return boto.sdb.connect_to_region(region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
		
	def sdb_domain_exists(self, domain_name_env):
		exists = None
		try:
			dom = self.sdb_conn.get_domain(domain_name_env, validate = True)
			if(dom):
				exists = True
		except boto.exception.SDBResponseError:
			exists = False
		return exists

	def sdb_create_domain(self, domain_name_env):
		dom = self.sdb_conn.create_domain(domain_name_env)
		return dom
	
	def sdb_get_domain(self, domain_name, auto_create_domain = True):
		"""
		Get the SimpleDB domain, and optionally create it if is does not yet exist
		"""
		
		# Actual domain name is specific to the environment by adding a prefix
		domain_name_env = self.domain_names[domain_name]
		
		dom = None
		try:
			dom = self.sdb_conn.get_domain(domain_name_env)
		except boto.exception.SDBResponseError:
			# Domain did not exist, create if we specified to
			if(auto_create_domain):
				if(self.sdb_domain_exists(domain_name_env) == False):
					dom = self.sdb_create_domain(domain_name_env)
			else:
				dom = None
		
		# Add the domain so we can use it again later
		self.domains[domain_name] = dom
		
		return dom

	def elife_get_article_S3_file_items(self, file_data_type = None, doi_id = None, last_updated_since = None, latest = None):
		"""
		From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
		  file_data_type options:   xml, pdf, img, suppl, video
			doi_id:                   five digit numeric string as the unique portion of the DOI
			last_updated_since:       only return items updated since the date provided
			latest:                   only return the latest item of each type
		"""
		
		date_format = "%Y-%m-%dT%H:%M:%S.000Z"
		
		file_data_types = ["xml", "pdf", "img", "suppl", "video"]
		
		domain_name = "S3FileLog"
		
		item_list = []
		
		domain_name_env = self.get_domain_name(domain_name)
		bucket_name = self.settings.bucket
		query = self.elife_get_article_S3_query(date_format, domain_name_env, file_data_types, bucket_name, file_data_type, doi_id, last_updated_since)

		dom = self.get_domain(domain_name)

		rs = dom.select(query)
		for j in rs:
			item_list.append(j)
			
		# Lastly, if we only want the latest file, then remove duplicates
		#  having the same DOI and file_data_type
		if(latest is True):
			item_list = self.elife_filter_latest_article_S3_file_items(item_list, file_data_types)
			
		return item_list
	
	def elife_get_article_S3_query(self, date_format, domain_name, file_data_types, bucket_name = None, file_data_type = None, doi_id = None, last_updated_since = None):
		"""
		Build a query for SimpleDB to get S3 elife-articles bucket data
		from the S3FileLog domain.
		"""
		
		query = ""

		# Assemble where clause
		where_clause = ""
		where_delimiter = " where"
		
		# Constrain to the specified bucket
		if(bucket_name):
			where_clause += where_delimiter + " bucket_name = '" + bucket_name + "'"
			where_delimiter = " and"
		
		name_present = False
		if(file_data_type):
			data_type_match = None
			
			for data_type in file_data_types:
				if(file_data_type == data_type):
					data_type_match = "'%." + data_type + "%'"

			if(data_type_match):
				where_clause += where_delimiter + " name like " + data_type_match
				where_delimiter = " and"
				name_present = True
		if(doi_id):
			where_clause += where_delimiter + " name like '" + doi_id + "/%'"
			where_delimiter = " and"
			name_present = True
		if(last_updated_since):
			# Select based on timestamp
			date_str = time.strptime(last_updated_since, date_format)
			timestamp = calendar.timegm(date_str)
			if(timestamp): 
				where_clause += where_delimiter + " last_modified_timestamp > '" + str(timestamp) + "'"
				where_delimiter = " and"
				
		# Add a name clause if none was added, or AWS complains about the orderby
		if(name_present == False):
			where_clause += where_delimiter + " name is not null"
			
		order_by = " order by name asc"
		
		# Assemble the query
		query = 'select * from ' + domain_name + ''
		query = query + where_clause
		query = query + order_by

		return query
	
	def elife_filter_latest_article_S3_file_items(self, item_list, file_data_types):
		"""
		Given a list of S3 article file items from the log, only return the latest item
		for a DOI and data file type (xml, img, etc.) listed in file_data_types
		"""
		
		# First assemble an array of elements to sort
		list_to_sort = []
		for item in item_list:
			# DOI
			doi_id = None
			doi_id = str(item['name']).split("/")[0]
			
			# Data type
			file_data_type = None
			name_parts = str(item['name']).split(".")
			try:
				if(name_parts[-1] in file_data_types):
					file_data_type = name_parts[-1]
				elif(name_parts[-2] in file_data_types):
					file_data_type = name_parts[-2]
				elif(name_parts[-3] in file_data_types):
					file_data_type = name_parts[-3]
			except IndexError:
				# No data type part found
				pass
			
			# Timestamp
			timestamp = None
			timestamp = item['last_modified_timestamp']
			
			elem = {}
			elem['doi_id'] = doi_id
			elem['file_data_type'] = file_data_type
			elem['timestamp'] = timestamp
			elem['item_name'] = item['item_name']
			
			list_to_sort.append(elem)
			
		# Second, sort the list by multiple attributes
		s = sorted(list_to_sort, key=itemgetter('timestamp'))
		s = sorted(s, key=itemgetter('file_data_type'))
		s = sorted(s, key=itemgetter('doi_id'))

		# Third, loop through sorted array and get a list of items to remove
		prev_item = None
		items_to_remove = []
		for item in s:
			if(prev_item is None):
				# Keep first item
				prev_item = item
				continue
			
			# Compare previous and current values, and if equal
			#  then remove the previous value from our master item list
			if(item['doi_id'] == prev_item['doi_id']
				 and item['file_data_type'] == prev_item['file_data_type']
				 ):
				items_to_remove.append(prev_item)
			
			prev_item = item
		
		# Fourth, remove the marked items from the list
		#  Not great for speed but hopefully fast enough when
		#  items to remove is small
		for item in item_list:
			for remove_item in items_to_remove:
				if(item['item_name'] == remove_item['item_name']
					 and item['last_modified_timestamp'] == remove_item['timestamp']
					 ):
					item_list.remove(item)

		return item_list