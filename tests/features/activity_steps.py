from lettuce import *
import activity
import json

@step('I can get a domain from the activity')
def get_domain_from_activity_object(step):
	assert world.activity_object.domain is not None, \
		"Got domain %s" % world.activity_object.domain
	
@step('I can get a task_list from the activity')
def get_task_list_from_activity_object(step):
	assert world.activity_object.task_list is not None, \
		"Got task_list %s" % world.activity_object.task_list
	
@step('I get the activity name (\S+)')
def get_activity_name(step, name):
	assert world.activity_object.name == name, \
		"Got name %s" % world.activity_object.name

@step('I get a result from the activity')
def get_result_from_activity_object(step):
	world.result = world.activity_object.do_activity(world.json)
	assert world.result is not None, \
		"Got result %s" % world.result
	
@step('I can get a domain from the workflow')
def get_domain_from_workflow_object(step):
	assert world.workflow_object.domain is not None, \
		"Got domain %s" % world.workflow_object.domain
	
@step('I can get a task_list from the workflow')
def get_task_list_from_workflow_object(step):
	assert world.workflow_object.task_list is not None, \
		"Got task_list %s" % world.workflow_object.task_list
	
@step('I get the workflow name (\S+)')
def get_workflow_name(step, name):
	assert world.workflow_object.name == name, \
		"Got name %s" % world.workflow_object.name
	
@step('I have the document name (\S+)')
def have_the_document_name(step, document_name):
	world.document_name = document_name
	assert world.document_name is not None, \
		"Got document %s" % world.document_name 
	
@step('I parse the document name with ArticleToFluidinfo')
def parse_the_document_name_with_ArticleToFluidinfo(step):
	world.activity_object.parse_document(world.document_name)
	assert world.activity_object.a is not None, \
		"Got article %s" % world.activity_object.a

@step('I get the DOI from the ArticleToFluidinfo article (\S+)')
def parse_the_document_name_with_ArticleToFluidinfo(step, doi):
	assert world.activity_object.a.doi == doi, \
		"Got doi %s" % world.activity_object.a.doi
	
@step('I read the file named document name with ArticleToFluidinfo')
def read_the_file_named_document_name_with_ArticleToFluidinfo(step):
	world.activity_object.fs.read_document_to_content(world.document_name)
	assert world.activity_object.fs.content is not None, \
		"Got content %s" % world.activity_object.fs.content
	
@step('I write the content from ArticleToFluidinfo to (\S+)')
def write_the_content_from_ArticleToFluidinfo(step, filename):
	world.activity_object.fs.write_content_to_document(filename)
	assert world.activity_object.fs.document is not None, \
		"Wrote document %s" % world.activity_object.fs.document

@step('I get the document name from ArticleToFluidinfo')
def get_the_document_name_from_ArticleToFluidinfo(step):
	world.document_name = world.activity_object.fs.get_document()
	assert world.document_name is not None, \
		"Got document %s" % world.document_name
	
@step('I get the document name from ArticleToFluidinfo as (\S+)')
def get_the_document_name_from_ArticleToFluidinfo_as(step, filename):
	world.document_name = world.activity_object.fs.get_document()
	assert world.document_name == filename, \
		"Got document %s" % world.document_name
	
@step('I have the item name (\S+)')
def have_the_item_name(step, item_name):
	world.item_name = item_name
	assert world.item_name is not None, \
		"Got item name %s" % world.item_name
	
@step('I have the item attr last_modified_timestamp (\S+)')
def have_the_item_attr_last_modified_timestamp(step, last_modified_timestamp):
	world.item_attrs = {}
	# Convert string to int to replicate real running action
	world.item_attrs['last_modified_timestamp'] = int(last_modified_timestamp)
	assert world.item_attrs is not None, \
		"Got item attributes %s" % world.item_attrs
	
@step('I get the log_item_name from the S3Monitor (\S+)')
def get_the_log_item_name_from_the_s3monitor(step, log_item_name):
	world.log_item_name = world.activity_object.get_log_item_name(world.item_name, world.item_attrs)
	assert world.log_item_name == log_item_name, \
		"Got log_item_name %s" % world.log_item_name

@step('I have the base name (\S+)')
def have_the_base_name(step, base_name):
	world.base_name = base_name
	assert world.base_name is not None, \
		"Got base_name %s" % world.base_name

@step('I have the timestamp (\S+)')
def have_the_timestamp(step, timestamp):
	# Takes a float, apparently
	world.timestamp = float(timestamp)
	assert world.timestamp is not None, \
		"Got timestamp %f" % world.timestamp

@step('I have the date format (\S+)')
def have_the_date_format(step, date_format):
	world.date_format = date_format
	assert world.date_format is not None, \
		"Got date_format %s" % world.date_format

@step('I get the expanded date attributes from S3Monitor using a timestamp')
def get_the_expanded_date_attributes_from_S3Monitor_using_a_timestamp(step):
	world.date_attrs = world.activity_object.get_expanded_date_attributes(world.base_name, world.date_format, world.timestamp)
	assert world.date_attrs is not None, \
		"Got date_attrs %s" % world.date_attrs

@step('I have the timestamp attribute (\S+)')
def have_the_timestamp_attribute(step, timestamp):
	key_name = world.base_name + '_timestamp'
	assert world.date_attrs[key_name] == float(timestamp), \
		"Got timestamp %s" % world.date_attrs[key_name]
	
@step('I have the date attribute (\S+)')
def have_the_date_attribute(step, date):
	key_name = world.base_name + '_date'
	assert world.date_attrs[key_name] == date, \
		"Got date %s" % world.date_attrs[key_name]
	
@step('I have the year attribute (\S+)')
def have_the_year_attribute(step, year):
	key_name = world.base_name + '_year'
	assert world.date_attrs[key_name] == year, \
		"Got date %s" % world.date_attrs[key_name]
	
@step('I have the month attribute (\S+)')
def have_the_month_attribute(step, month):
	key_name = world.base_name + '_month'
	assert world.date_attrs[key_name] == month, \
		"Got date %s" % world.date_attrs[key_name]
	
@step('I have the day attribute (\S+)')
def have_the_day_attribute(step, day):
	key_name = world.base_name + '_day'
	assert world.date_attrs[key_name] == day, \
		"Got date %s" % world.date_attrs[key_name]
	
@step('I have the time attribute (\S+)')
def have_the_time_attribute(step, time):
	key_name = world.base_name + '_time'
	assert world.date_attrs[key_name] == time, \
		"Got time %s" % world.date_attrs[key_name]