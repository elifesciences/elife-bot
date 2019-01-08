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
