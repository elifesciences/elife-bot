from lettuce import *
import activity
import json
import datetime
import os
import provider.ejp as ejplib

@step('I create a ejp provider')
def i_create_a_ejp_provider(step):
  try:
    world.settings = world.settings
  except AttributeError:
    world.settings = None

  world.ejp = ejplib.EJP(world.settings, world.tmp_dir)
  assert world.ejp is not None, \
    "Got ejp %s" % world.ejp
    
@step('I parse author file the document with ejp')
def i_parse_author_file_the_document_with_ejp(step):
  (world.column_headings, world.author_rows) = world.ejp.parse_author_file(world.document)
  assert world.column_headings is not None, \
    "Got column_headings %s" % world.column_headings

@step('I have the ejp document (\S+)')
def i_have_the_ejp_document_count_count(step, ejp_document):
  assert world.ejp_document == ejp_document, \
    "Got ejp_document %s" % world.ejp_document

@step('I have the column headings (.+)')
def i_have_the_column_headings(step, column_headings):
  assert str(world.column_headings) == str(column_headings), \
    "Got column_headings %s " % str(world.column_headings)

@step('I have the authors count (\d+)')
def i_have_the_authors_count(step, count):
  assert len(world.authors) == int(count), \
    "Got count %s " % len(world.authors)
  
@step('I get the authors from ejp')
def i_get_the_authors_from_ejp(step):
  try:
    world.corr = world.corr
  except AttributeError:
    world.corr = None
  
  (world.column_headings, world.authors) = world.ejp.get_authors(world.doi_id, world.corr, world.document)
  assert world.authors is not None, \
    "Got authors %s" % world.authors
  
@step('I have corresponding (\S+)')
def i_have_corresponding(step, corr):
  if(corr == "None"):
    world.corr = None
    assert world.corr is None, \
      "Got corr %s" % world.corr
  elif(corr == "True"):
    world.corr = True
    assert world.corr is True, \
      "Got corr %s" % world.corr
  elif(corr == "False"):
    world.corr = False
    assert world.corr is False, \
      "Got corr %s" % world.corr
  else:
    world.corr = corr
    assert world.corr is not None, \
      "Got corr %s" % world.corr
    
@step('I have file type (\S+)')
def i_have_file_type_file_type(step, file_type):
  world.file_type = file_type
  assert world.file_type is not None, \
    "Got file_type %s" % world.file_type
  
@step('I find latest s3 file name using ejp')
def i_find_latest_s3_file_name_using_ejp(step):
  world.s3_file_name = world.ejp.find_latest_s3_file_name(world.file_type, world.json)
  assert world.s3_file_name is not None, \
    "Got s3_file_name %s" % world.s3_file_name
    
@step('I have s3 file name (\S+)')
def i_have_s3_file_name_s3_file_name(step, s3_file_name):
  assert world.s3_file_name == s3_file_name, \
    "Got s3_file_name %s " % world.s3_file_name
  
@step('I parse editor file the document with ejp')
def i_parse_editor_file_the_document_with_ejp(step):
  (world.column_headings, world.editor_rows) = world.ejp.parse_editor_file(world.document)
  assert world.column_headings is not None, \
    "Got column_headings %s" % world.column_headings
    
@step('I get the editors from ejp')
def i_get_the_editors_from_ejp(step):
  
  (world.column_headings, world.editors) = world.ejp.get_editors(world.doi_id, world.document)
  assert world.editors is not None, \
    "Got editors %s" % world.editors

@step('I have the editors count (\d+)')
def i_have_the_editors_count(step, count):
  assert len(world.editors) == int(count), \
    "Got count %s " % len(world.editors)
