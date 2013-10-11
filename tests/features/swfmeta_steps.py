from lettuce import *
import activity
import json

@step('I have imported the SWFMeta provider module')
def import_swfmeta_provider_module(step):
  imported = None
  # Check for world.settings, if not specified set to None
  try:
    if not world.settings:
      world.settings = None
  except AttributeError:
    world.settings = None
    
  try:
    import provider.swfmeta as swfmetalib
    world.swfmeta = swfmetalib.SWFMeta(world.settings)
    imported = True
  except:
    imported = False
  assert imported is True, \
    "SWFMeta module was imported"
    
@step('I have the workflow id (\S+)')
def have_workflow_id(step, workflow_id):
  if(workflow_id == "None"):
    world.workflow_id = None
    assert world.workflow_id is None, \
      "Got workflow_id %s" % world.workflow_id
  else:
    world.workflow_id = workflow_id
    assert world.workflow_name is not None, \
      "Got workflow_id %s" % world.workflow_id
    
@step('I have the domain (\S+)')
def have_the_domain(step, domain):
  if(domain == "None"):
    world.domain = None
    assert world.domain is None, \
      "Got domain %s" % world.domain
  else:
    world.domain = domain
    assert world.domain is not None, \
      "Got domain %s" % world.domain
    
@step('I check is workflow open using the SWFMeta provider')
def i_check_is_workflow_open_using_the_swfmeta_provider(step):
  world.is_open = world.swfmeta.is_workflow_open(
    infos = world.json,
    domain = world.domain,
    workflow_name = world.workflow_name,
    workflow_id = world.workflow_id)
  assert world.is_open is not None, \
    "Got is_open %s" % world.is_open
  
@step('I get is open (\S+)')
def i_get_is_open(step, is_open):
  if(is_open == "True"):
    assert world.is_open is True, \
      "Got world.is_open %s" % world.is_open
  elif(is_open == "False"):
    assert world.is_open is False, \
      "Got world.is_open %s" % world.is_open
    
@step('I get last completed workflow execution startTimestamp using the SWFMeta provider')
def i_get_last_completed_workflow_execution_starttimestamp_using_the_swfmeta_provider(step):
  world.startTimestamp = world.swfmeta.get_last_completed_workflow_execution_startTimestamp(
    infos = world.json,
    domain = world.domain,
    workflow_name = world.workflow_name,
    workflow_id = world.workflow_id)
  assert world.startTimestamp is not None, \
    "Got startTimestamp %s" % world.startTimestamp
  
@step('I get the startTimestamp (\S+)')
def i_get_the_starttimestamp(step, startTimestamp):
  assert str(world.startTimestamp) == str(startTimestamp), \
    "Got world.startTimestamp %s" % world.startTimestamp
