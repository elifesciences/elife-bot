import json
import random
import datetime
import calendar
import time
from operator import itemgetter, attrgetter

import boto.sdb

import boto.s3
from boto.s3.connection import S3Connection

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
		self.domain_names['EmailQueue'] = "EmailQueue" + domain_postfix
		
		# Actual domain connections (boto objects), save them for future use once gotten
		self.domains = {}
		
		self.sdb_conn = None

		# S3 bucket where email body content is stored
		self.email_body_bucket = settings.bot_bucket
		
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
	
	def escape(self, val):
		"""
		Escape single apostrophe with double apostrophe
		for strings used in SimpleDB queries
		"""
		if(val):
			val = str(val).replace("'", "''")
		return val

	def elife_get_POA_delivery_S3_file_items(self, last_updated_since = None):
		"""
		From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
			last_updated_since:       only return items updated since the date provided
		"""
		
		date_format = "%Y-%m-%dT%H:%M:%S.000Z"
		
		domain_name = "S3FileLog"
		
		item_list = []
		
		domain_name_env = self.get_domain_name(domain_name)
		bucket_name = self.settings.poa_bucket
		query = self.elife_get_POA_delivery_S3_query(date_format, domain_name_env, bucket_name, last_updated_since)

		dom = self.get_domain(domain_name)

		rs = dom.select(query)
		for j in rs:
			item_list.append(j)
		
		return item_list

	def elife_get_POA_delivery_S3_query(self, date_format, domain_name, bucket_name = None, last_updated_since = None):
		"""
		Build a query for SimpleDB to get S3 poa_bucket bucket data
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
		
		last_updated_since_present = False

		if(last_updated_since):
			# Select based on timestamp
			date_str = time.strptime(last_updated_since, date_format)
			timestamp = calendar.timegm(date_str)
			if(timestamp): 
				where_clause += where_delimiter + " last_modified_timestamp > '" + str(timestamp) + "'"
				where_delimiter = " and"
				last_updated_since_present = True
				
		# Add a name clause if none was added, or AWS complains about the orderby
		if(last_updated_since_present == False):
			where_clause += where_delimiter + " last_modified_timestamp is not null"
			
		order_by = " order by last_modified_timestamp asc"
		
		# Assemble the query
		query = 'select * from ' + domain_name + ''
		query = query + where_clause
		query = query + order_by

		return query

	def elife_get_article_S3_file_items(self, file_data_type = None, doi_id = None, last_updated_since = None, latest = None):
		"""
		From the SimpleDB domain for the S3FileLog, return a list of matching item to the attributes
		  file_data_type options:   xml, pdf, img, suppl, video, svg, jpg
			doi_id:                   five digit numeric string as the unique portion of the DOI
			last_updated_since:       only return items updated since the date provided
			latest:                   only return the latest item of each type
		"""
		
		date_format = "%Y-%m-%dT%H:%M:%S.000Z"
		
		file_data_types = ["xml", "pdf", "img", "suppl", "video", "svg", "jpg"]
		
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
		for remove_item in items_to_remove:
			for item in item_list:
				if(item['item_name'] == remove_item['item_name']
					 and item['last_modified_timestamp'] == remove_item['timestamp']
					 ):
					item_list.remove(item)

		return item_list
	
	def elife_get_email_queue_items(self, query_type = "items", sort_by = None, limit = None, sent_status = None, email_type = None, doi_id = None, date_scheduled_before = None, date_sent_before = None, recipient_email = None):
		"""
		From the SimpleDB domain for the EmailQueue, return a list of matching item to the attributes
		  query_type:               Type of query: "items" return items, "count" return a count of items
			sent_status:              True, False, None - Booleans will be converted to strings for the query
			email_type:               template type or email type
			doi_id:                   five digit numeric string as the unique portion of the DOI
			date_scheduled_before:    only return items scheduled to send before the date provided, in the date format
			date_sent_before:         only return items that were sent before the date provided, in the date format
			recipient_email:
		"""
		
		date_format = "%Y-%m-%dT%H:%M:%S.000Z"
		
		domain_name = "EmailQueue"
		
		item_list = []
		
		domain_name_env = self.get_domain_name(domain_name)
		query = self.elife_get_email_queue_query(
			date_format,
			domain_name_env,
			query_type,
			sort_by,
			limit,
			sent_status,
			email_type,
			doi_id,
			date_scheduled_before,
			date_sent_before,
			recipient_email
			)

		dom = self.get_domain(domain_name)

		rs = dom.select(query)
		for j in rs:
			item_list.append(j)

		return item_list
	
	def elife_get_email_queue_query(self, date_format, domain_name, query_type = "items", sort_by = None, limit = None, sent_status = None, email_type = None, doi_id = None, date_scheduled_before = None, date_sent_before = None, recipient_email = None):
		"""
		Build a query for SimpleDB to get EmailQueue data
		from the EmailQueue domain.
		"""
		
		query = ""

		# Double-check the query_type if None is supplied
		#  This helps when running tests and setting a default
		if(query_type is None):
			query_type = "items"

		# Assemble where clause
		where_clause = ""
		where_delimiter = " where"
		order_by = ""
		limit_clause = ""
		
		if(sent_status):
			where_clause += where_delimiter + " sent_status = '" + str(sent_status) + "'"
			where_delimiter = " and"
		else:
			where_clause += where_delimiter + " sent_status is null"
			where_delimiter = " and"
		
		if(email_type):
			where_clause += where_delimiter + " email_type = '" + escape(email_type) + "'"
			where_delimiter = " and"
		
		if(doi_id):
			where_clause += where_delimiter + " doi_id = '" + doi_id + "'"
			where_delimiter = " and"

		if(date_scheduled_before):
			# Select based on timestamp
			date_str = time.strptime(date_scheduled_before, date_format)
			timestamp = calendar.timegm(date_str)
			if(timestamp): 
				where_clause += where_delimiter + " date_scheduled_timestamp < '" + str(timestamp) + "'"
				where_delimiter = " and"
				
		if(date_sent_before):
			# Select based on timestamp
			date_str = time.strptime(date_sent_before, date_format)
			timestamp = calendar.timegm(date_str)
			if(timestamp): 
				where_clause += where_delimiter + " date_sent_timestamp < '" + str(timestamp) + "'"
				where_delimiter = " and"
				
		if(recipient_email):
			where_clause += where_delimiter + " recipient_email = '" + recipient_email + "'"
			where_delimiter = " and"
				
		# Add a where clause if the field was added, or AWS complains about the orderby
		if(sort_by):
			where_clause += where_delimiter + " " + sort_by + " is not null"
			order_by = " order by " + sort_by + " asc"
			
		# Add a limit
		if(limit):
			limit_clause += " limit " + str(limit)
		
		# Assemble the query
		query = ""
		if(query_type == "items"):
			query = query + 'select * from '
		elif(query_type == "count"):
			query = query + 'select count(*) from '
		query = query + domain_name + ''
		query = query + where_clause
		query = query + order_by
		query = query + limit_clause

		return query
	
	def elife_get_unique_email_queue_item_name(self, domain_name = None, check_is_unique = None, timestamp = None, doi_id = None, email_type = None, recipient_email = None):
		"""
		Given a bunch of variables, assemble a SimpleDB item_name
		that we can expect to be relatively unique for an email queue
		item, check if it does not yet exist, if so, increment and make a new key

		Supplying a timestamp is only needed for when running tests, otherwise the
		current timestamp is used
		
		"""
		item_name = ""
		
		# Default domain name
		if(not domain_name):
			domain_name = "EmailQueue"
		
		if(timestamp):
			current_timestamp = timestamp
		else:
			current_timestamp = calendar.timegm(time.gmtime())

		item_name = str(int(current_timestamp))
		if(doi_id):
			item_name += "__" + str(doi_id)
		if(email_type):
			item_name += "__" + str(email_type)
		if(recipient_email):
			item_name += "__" + str(recipient_email)
		
		# Test if item already exists, if so add an increment to it and try again
		unique_item_name = None
		if(check_is_unique and domain_name is None):
			# Cannot check if unique without supplying a domain name
			# will end up returning null
			pass
		elif(check_is_unique is not None and domain_name is not None):
			# Check the domain for a unique item name
			simpledb_item = self.get_item(domain_name, item_name, consistent_read=True)
			if(simpledb_item is None):
				# Item does not exist, is unique
				unique_item_name = item_name
			if(unique_item_name is None):
				# Item was not unique, try to create one
				for i in range(1, 100):
					new_item_name = item_name + "__" + str(i).zfill(3)
					simpledb_item = self.get_item(domain_name, new_item_name, consistent_read=True)
					if(simpledb_item is None):
						# Item does not exist, is unique
						unique_item_name = new_item_name
					if(unique_item_name is not None):
						break
		else:
			# Default
			unique_item_name = item_name

		return unique_item_name

	def elife_add_email_to_email_queue(self, recipient_email, sender_email, email_type, date_added_timestamp = None, date_scheduled_timestamp = 0, doi_id = None, format = "text", recipient_name = None, sender_name = None, subject = None, body = None, add = True):
		"""
		Given all the necessary details to send an email
		add an email to the email queue
		Body and subject must be ready to send, i.e. no template tags requiring replacement
		All duplicate email checking, if necessary, must be done before adding it to the queue
		  via this function

		add = True - default is add the email; if false assemble the attributes and return them,
		             for running tests

		Some schema detail:
		
		body                      body of the message to send
		date_added_timestamp      date added to the queue, current timestamp if not supplied
		date_scheduled_timestamp  date scheduled to send, 0 if not supplied
		date_sent_timestamp       None when added, since it is not sent yet
		doi_id                    DOI 5 digits
		email_type                Unique template or email type name for checking duplicates
		format                    "text" or "html", as used by Amazon SES
		recipient_email           Recipient email
		recipient_name            Recipient name (optional)
		sender_email              Sender email
		sender_name               Sender name (optional)
		sent_status               Sent status is None when first added to the queue
		subject                   Subject of the email
		
		"""
		
		# Default SimpleDB domain
		domain_name = "EmailQueue"
		
		item_attrs = {}
		
		# Mandatory
		if(recipient_email):
			item_attrs["recipient_email"] = recipient_email
		else:
			return None
		
		if(sender_email):
			item_attrs["sender_email"] = sender_email
		else:
			return None
		
		if(email_type):
			item_attrs["email_type"] = email_type
		else:
			return None
		
		# Default
		if(format):
			item_attrs["format"] = format
		else:
			item_attrs["format"] = "text"
		
		# Dates
		if(date_added_timestamp):
			item_attrs["date_added_timestamp"] = date_added_timestamp
		else:
			item_attrs["date_added_timestamp"] = calendar.timegm(time.gmtime())
			
		if(date_scheduled_timestamp):
			item_attrs["date_scheduled_timestamp"] = date_scheduled_timestamp
		else:
			# Schedule immediately
			item_attrs["date_scheduled_timestamp"] = 0

		# Optional
		item_attrs["doi_id"] = doi_id

		if(recipient_name):
			item_attrs["recipient_name"] = recipient_name
			
		if(sender_name):
			item_attrs["sender_name"] = sender_name
			
		if(subject):
			item_attrs["subject"] = subject

		if(add is True):
			# Add to the queue
			# Get a unique item_name
			unique_item_name = self.elife_get_unique_email_queue_item_name(
				check_is_unique = True,
				timestamp       = item_attrs["date_added_timestamp"],
				doi_id          = item_attrs["doi_id"],
				email_type      = item_attrs["email_type"],
				recipient_email = item_attrs["recipient_email"])
			
			if(unique_item_name):
				
				if(body):
					# Save the email body to S3 bucket
					delimiter = "/"
					body_s3key = "email" + delimiter + email_type + delimiter + unique_item_name
					self.elife_save_email_body_to_s3(
						body_s3key = body_s3key,
						body = body
						)
					item_attrs["body_s3key"] = body_s3key
					
				# Add the item to the SimpleDB
				self.put_attributes(domain_name, unique_item_name, item_attrs)
				return True
			else:
				return False
			
		else:
			return item_attrs
		
		# Default
		return None
	
	def elife_save_email_body_to_s3(self, body_s3key, body):
		"""
		From the S3 bucket, get the object content for the body_s3key key
		"""
		
		# Connect to S3 and the bucket
		bucket_name = self.email_body_bucket
		s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
		bucket = s3_conn.lookup(bucket_name)
		s3key = boto.s3.key.Key(bucket)
		# Create the key and save to body to it
		s3key.key = body_s3key
		s3key.set_contents_from_string(body)

	