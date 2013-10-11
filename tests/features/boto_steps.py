from lettuce import *
import importlib
import workflow
import activity

@step('Given I have imported a settings module')
def import_settings_module(step):
	imported = None
	try:
		import settings as settingsLib
		world.settingsLib = settingsLib
		imported = True
	except:
		imported = False
	assert imported is True, \
		"Settings module was imported"
	
@step('I have the settings environment (\S+)')
def get_settings_environment(step, env):
	world.env = env
	assert world.env is not None, \
		"Got env %s" % world.env 

@step('I get the settings')
def get_the_settings(step):
	world.settings = world.settingsLib.get_settings(world.env)
	assert world.settings is not None, \
		"Got settings"

@step('I have a setting for (\S+)')
def have_a_setting(step, identifier):
	ident = eval("world.settings." + identifier)
	assert ident is not None, \
		"Got setting %s" % ident
	
@step('I have imported the boto module')
def import_boto_module(step):
	imported = None
	try:
		import boto
		world.boto = boto
		imported = True
	except:
		imported = False
	assert imported is True, \
		"boto module was imported"
	
@step('I have imported the boto.swf module')
def import_boto_swf_module(step):
	imported = None
	try:
		import boto.swf
		world.boto.swf = boto.swf
		imported = True
	except:
		imported = False
	assert imported is True, \
		"boto.swf module was imported"

@step('I connect to Amazon SWF')
def connect_to_amazon_swf(step):
	world.conn = world.boto.swf.layer1.Layer1(world.settings.aws_access_key_id, world.settings.aws_secret_access_key)
	assert world.conn is not None, \
		"Connected to Amazon SWF %s" % world.conn

@step('I can describe the SWF domain')
def describe_the_swf_domain(step):
	dom_response = world.conn.describe_domain(world.settings.domain)
	assert dom_response is not None, \
		"The SWF domain is %s" % dom_response
	
@step('I have the workflow name (\S+)')
def have_workflow_name(step, workflow_name):
	if(workflow_name == "None"):
		world.workflow_name = None
		assert world.workflow_name is None, \
			"Got workflow_name %s" % world.workflow_name
	else:
		world.workflow_name = workflow_name
		assert world.workflow_name is not None, \
			"Got workflow_name %s" % world.workflow_name
	
@step('I have a workflow object')
def get_workflow_object(step):
	# Import the workflow libraries
	class_name = "workflow_" + world.workflow_name
	module_name = "workflow." + class_name
	importlib.import_module(module_name)
	full_path = "workflow." + class_name + "." + class_name
	# Create the workflow object
	f = eval(full_path)
	logger = None
	try:
		world.conn = world.conn
	except AttributeError:
		world.conn = None
	world.workflow_object = f(world.settings, logger, world.conn)
	assert world.workflow_object is not None, \
		"Got workflow_object %s" % world.workflow_object
	
@step('I have the workflow version')
def get_workflow_version(step):
	world.workflow_version = world.workflow_object.version
	assert world.workflow_version is not None, \
		"Got workflow_version %s" % world.workflow_version
	
@step('I can describe the SWF workflow type')
def describe_the_swf_workflow_type(step):
	response = world.workflow_object.describe()
	assert response is not None, \
		"The SWF workflow type responded %s" % response
	
@step('I have the activity name (\S+)')
def have_activity_name(step, activity_name):
	world.activity_name = activity_name
	assert world.activity_name is not None, \
		"Got activity_name %s" % world.activity_name 

@step('I have the activityId (\S+)')
def have_activity_name(step, activityId):
	world.activityId = activityId
	assert world.activityId is not None, \
		"Got activityId %s" % world.activityId 

@step('I have an activity object')
def get_activity_object(step):
	# Import the activity libraries
	class_name = "activity_" + world.activity_name
	module_name = "activity." + class_name
	importlib.import_module(module_name)
	full_path = "activity." + class_name + "." + class_name
	# Create the workflow object
	f = eval(full_path)
	logger = None
	try:
		world.conn = world.conn
	except AttributeError:
		world.conn = None
	# Assemble a tiny SWF activity_task to give it a specific ID
	try:
		world.activityId = world.activityId
	except AttributeError:
		world.activityId = None
	if(world.activityId is not None):
		world.activity_task = {}
		world.activity_task["activityId"] = world.activityId
	else:
		world.activity_task = None
	# Throw out and recreate the object
	#world.activity_object = None
	world.activity_object = f(world.settings, logger, world.conn, None, world.activity_task)
	assert world.activity_object is not None, \
		"Got activity_object %s" % world.activity_object
	
@step('I have the activity version')
def get_activity_version(step):
	world.activity_version = world.activity_object.version
	assert world.activity_version is not None, \
		"Got activity_version %s" % world.activity_version
	
@step('I can describe the SWF activity type')
def describe_the_swf_activity_type(step):
	response = world.conn.describe_activity_type(world.settings.domain, world.activity_name, world.activity_version)
	assert response is not None, \
		"The SWF activity type responded %s" % response

@step('Finally I can disconnect from Amazon SWF')
def disconnect_from_amazon_swf(step):
	# No disconnect required
	pass

@step('I have the simpledb region from the settings')
def have_simpledb_region_from_the_settings(step):
	assert world.settings.simpledb_region is not None, \
		"Got simpledb_region %s" % world.settings.simpledb_region

@step('I have imported the boto.sdb module')
def import_boto_sdb_module(step):
	imported = None
	try:
		import boto.sdb
		world.boto.sdb = boto.sdb
		imported = True
	except:
		imported = False
	assert imported is True, \
		"boto.sdb module was imported"

@step('I connect to Amazon SimpleDB')
def connect_to_amazon_simpledb(step):
	world.db_conn = world.boto.sdb.connect_to_region(world.settings.simpledb_region, aws_access_key_id = world.settings.aws_access_key_id, aws_secret_access_key = world.settings.aws_secret_access_key)
	assert world.db_conn is not None, \
		"Connected to Amazon SimpleDB %s" % world.db_conn
	
@step('I can list the SimpleDB domains')
def list_the_simpledb_domains(step):
	world.sdb_domains = world.db_conn.get_all_domains()
	assert world.sdb_domains is not None, \
		"Got sdb domains %s" % world.sdb_domains

@step('Finally I can disconnect from Amazon SimpleDB')
def disconnect_from_amazon_simpledb(step):
	# No disconnect required
	pass
	  
		