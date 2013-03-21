from lettuce import *
import os
import json

@step('I have a response JSON document (\S+)')
def have_a_response_JSON_document(step, document):
	#document = document.lstrip('"').rstrip('"')
	world.document = document
	assert world.document is not None, \
		"Got document %s" % world.document 
	
@step('I get JSON from the document')
def get_JSON_from_the_document(step):
	f = open(world.document)
	world.json_string = f.read()
	f.close()
	#world.json_string = open(os.getcwd() + os.sep + world.document)
	assert world.json_string is not None, \
		"Got json_string %s" % world.json_string

@step('I parse the JSON string')
def parse_the_JSON_string(step):
	world.json = json.loads(world.json_string)
	assert world.json is not None, \
		"Got json %s" % json.dumps(world.json)

@step('I have a decider module')
def have_a_decider_module(step):
	imported = None
	try:
		import decider as decider
		world.decider = decider
		imported = True
	except:
		imported = False
	assert imported is True, \
		"Got a decider module"

@step('I have a worker module')
def have_a_worker_module(step):
	imported = None
	try:
		import worker as worker
		world.worker = worker
		imported = True
	except:
		imported = False
	assert imported is True, \
		"Got a worker module"

@step('I get the taskToken using a decider')
def get_the_taskToken_using_a_decider(step):
	world.taskToken = world.decider.get_taskToken(world.json)
	assert world.taskToken is not None, \
		"Got taskToken %s" % world.taskToken

@step('I get the taskToken using a worker')
def get_the_taskToken_using_a_worker(step):
	world.taskToken = world.worker.get_taskToken(world.json)
	assert world.taskToken is not None, \
		"Got taskToken %s" % world.taskToken

@step('I have the taskToken (\S+)')
def have_the_taskToken(step, taskToken):
	assert world.taskToken == taskToken, \
		"Got %s" % world.taskToken

@step('I get the workflowType')
def get_the_workflowType(step):
	world.workflowType = world.decider.get_workflowType(world.json)
	assert world.workflowType is not None, \
		"Got workflowType %s" % world.workflowType

@step('I have the workflowType (\S+)')
def have_the_workflowType(step, workflowType):
	assert world.workflowType == workflowType, \
		"Got %s" % world.workflowType
	
@step('I get the activityType')
def get_the_activityType(step):
	world.activityType = world.worker.get_activityType(world.json)
	assert world.activityType is not None, \
		"Got activityType %s" % world.activityType

@step('I have the activityType (\S+)')
def have_the_activityType(step, activityType):
	assert world.activityType == activityType, \
		"Got %s" % world.activityType
	
@step('I get the activity_name')
def get_the_activity_name(step):
	world.activity_name = world.worker.get_activity_name(world.activityType)
	assert world.activity_name is not None, \
		"Got activity_name %s" % world.activity_name

@step('I have the activity_name (\S+)')
def have_the_activity_name(step, activity_name):
	assert world.activity_name == activity_name, \
		"Got %s" % world.activity_name
	
@step('I get the input using a worker')
def get_the_input_using_a_worker(step):
	world.input = world.worker.get_input(world.json)
	assert world.input is not None, \
		"Got input %s" % world.input

@step('I get the input using a decider')
def get_the_input_using_a_decider(step):
	world.input = world.decider.get_input(world.json)
	assert world.input is not None, \
		"Got input %s" % world.input

@step('Input contains (\S+)')
def input_contains(step, element):
	# Simplified the test on data since JSON comparisons are too complex
	value = None
	try:
		value = world.input[element]
	except(KeyError, TypeError):
		value = None
	assert value is not None, \
		"Got %s" % world.input
	
@step('Input element (\S+) is instanceof (\S+)')
def input_element_is_instanceof(step, element, datatype):
	value = None
	try:
		value = world.input[element]
	except(KeyError):
		value = None
	assert isinstance(value, eval(datatype)), \
		"Got %s" % type(value)
