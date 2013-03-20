from lettuce import *

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
	
@step('And I have the settings environment (\S+)')
def get_settings_environment(step, env):
	world.env = env
	assert world.env is not None, \
		"Got env %s" % world.env 

@step('I get the settings')
def get_the_settings(step):
	world.settings = world.settingsLib.get_settings(world.env)
	assert world.settings is not None, \
		"Got settings"

@step('Then I have a setting for (\S+)')
def have_a_setting(step, identifier):
	indent = eval("world.settings." + identifier)
	assert indent is not None, \
		"Got setting %s" % indent
	
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

@step('Finally I can disconnect from Amazon SWF')
def disconnect_from_amazon_swf(step):
	# No disconnect required
	pass

	  
		