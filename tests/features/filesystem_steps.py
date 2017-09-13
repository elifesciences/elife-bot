from lettuce import *
import activity
import json
import datetime
import os
import provider.filesystem as fslib

@step('I have a tmp_base_dir (\S+)')
def i_have_a_tmp_base_dir(step, tmp_base_dir):
  world.tmp_base_dir = tmp_base_dir
  assert world.tmp_base_dir is not None, \
    "Got tmp_base_dir %s" % world.tmp_base_dir

@step('I have test name (\S+)')
def i_have_test_name_test_name(step, test_name):
  world.test_name = test_name
  assert world.test_name is not None, \
    "Got test name %s" % world.test_name
    
@step('I get the current datetime')
def i_get_the_current_datetime(step):
  world.datetime = datetime.datetime.utcnow().strftime('%Y-%m-%d.%H.%M.%S')
  assert world.datetime is not None, \
    "Got datetime %s" % world.datetime

@step('I get the tmp_dir from the world')
def i_get_the_tmp_dir_from_the_world(step):
  # From variables assemble a unique tmp_dir directory name
  tmp_dir = ""
  if(world.tmp_base_dir):
    tmp_dir += world.tmp_base_dir + os.sep
  if(world.datetime):
    tmp_dir += world.datetime
  if(world.test_name):
    tmp_dir += "." + world.test_name
  if(tmp_dir == ""):
    tmp_dir = None
  world.tmp_dir = tmp_dir
  # also try to create the directory if it does not exist
  try:
    os.mkdir(world.tmp_dir)
  except OSError as e:
    pass
  assert world.tmp_dir is not None, \
    "Got tmp_dir %s" % world.tmp_dir
    
@step('I create a filesystem provider')
def i_create_a_filesystem_provider(step):
  world.fs = fslib.Filesystem(world.tmp_dir)
  assert world.fs is not None, \
    "Got fs %s" % world.fs
    
@step('I write the document to tmp_dir with filesystem')
def i_write_the_document_to_tmp_dir_with_filesystem(step):
  world.fs.write_document_to_tmp_dir(world.document)
  assert world.fs.document is not None, \
    "Got document %s" % world.fs.document
    
@step('I get the filesystem document')
def i_get_the_filesystem_document(step):
  world.filesystem_document = world.fs.get_document()
  assert world.filesystem_document is not None, \
    "Got filesystem_document %s" % world.filesystem_document
    
@step('I have the filesystem document count (\d+)')
def i_have_the_filesystem_document_count(step, count):
  world.count = len(world.filesystem_document)
  assert world.count == int(count), \
    "Got count %s" % world.count


