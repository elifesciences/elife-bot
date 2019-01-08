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
