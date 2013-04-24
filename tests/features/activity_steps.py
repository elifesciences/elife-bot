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