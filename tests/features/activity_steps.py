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
	world.activity_object.read_document_to_content(world.document_name)
	assert world.activity_object.content is not None, \
		"Got content %s" % world.activity_object.content
	
@step('I write the content from ArticleToFluidinfo to (\S+)')
def write_the_content_from_ArticleToFluidinfo(step, filename):
	world.activity_object.write_content_to_document(filename)
	assert world.activity_object.document is not None, \
		"Wrote document %s" % world.activity_object.document

@step('I get the document name from ArticleToFluidinfo')
def get_the_document_name_from_ArticleToFluidinfo(step):
	world.document_name = world.activity_object.get_document()
	assert world.document_name is not None, \
		"Got document %s" % world.document_name
	
@step('I get the document name from ArticleToFluidinfo as (\S+)')
def get_the_document_name_from_ArticleToFluidinfo_as(step, filename):
	world.document_name = world.activity_object.get_document()
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

	
