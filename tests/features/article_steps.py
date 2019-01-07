from lettuce import *
import activity
import json
import datetime
import time
import os
import provider.article as articlelib

@step('I create an article provider')
def i_create_an_article_provider(step):
  try:
    world.settings = world.settings
  except AttributeError:
    world.settings = None
    
  try:
    world.tmp_dir = world.tmp_dir
  except AttributeError:
    world.tmp_dir = None

  world.article = articlelib.article(world.settings, world.tmp_dir)
  assert world.article is not None, \
    "Got article %s" % world.article

@step('I have a doi (\S+)')
def i_have_a_doi(step, doi):
  world.doi = doi
  assert world.doi is not None, \
    "Got doi %s" % world.doi
  
@step('I have a doi_id (\d+)')
def i_have_a_doi_id(step, doi_id):
  world.doi_id = int(doi_id)
  assert world.doi_id is not None, \
    "Got doi_id %s" % world.doi_id

@step('I parse the document with the article provider')
def i_parse_the_document_with_the_article_provider(step):
  world.parsed = world.article.parse_article_file(world.document_name)
  assert world.parsed is True, \
    "Got parsed %s" % world.parsed

@step(u'I get was poa doi ids using the article provider')
def i_get_was_poa_doi_ids_using_the_article_provider(step):
  force = False
  world.was_poa_doi_ids = world.article.get_was_poa_doi_ids(force, world.folder_names, world.s3_key_names)
  assert world.was_poa_doi_ids is not None, \
    "Got was_poa_doi_ids %s" % json.dumps(world.was_poa_doi_ids)

@step(u'I have poa doi ids equal to world was poa doi ids')
def i_have_poa_doi_ids_equal_to_world_was_poa_doi_ids(step):
  assert world.was_poa_doi_ids == world.poa_doi_ids, \
    "Got was_poa_doi_ids %s" % json.dumps(world.was_poa_doi_ids)
  
@step(u'I check was ever poa (\S+) using the article provider')
def i_check_was_ever_poa_using_the_article_provider(step, doi_id):
  world.was_ever_poa = world.article.check_was_ever_poa(doi_id)
  assert world.was_ever_poa is not None, \
    "Got was_ever_poa %s" % world.was_ever_poa

@step(u'I get was ever poa is (\S+)')
def i_get_was_ever_poa_is_true(step, was_ever_poa):
  if was_ever_poa == "True":  was_ever_poa = True
  if was_ever_poa == "False": was_ever_poa = False
  assert world.was_ever_poa == was_ever_poa, \
    "Got was_ever_poa %s" % world.was_ever_poa
  
@step(u'I have the pub event type (\S+)')
def i_have_the_pub_event_type_pub_event_type(step,  pub_event_type):
  world.pub_event_type = pub_event_type
  assert world.pub_event_type is not None, \
    "Got pub_event_type %s" % world.pub_event_type
  
@step(u'I get article bucket published dates using the article provider')
def i_get_article_bucket_published_dates_using_the_article_provider(step):
  force = False
  world.article_bucket_published_dates = world.article.get_article_bucket_published_dates(
    force, world.folder_names, world.s3_key_names)
  assert world.article_bucket_published_dates is not None, \
    "Got article_bucket_published_dates %s" % json.dumps(world.article_bucket_published_dates)

@step(u'I get article bucket pub date using the article provider')
def i_get_article_bucket_pub_date_using_the_article_provider(step):
  world.pub_date = world.article.get_article_bucket_pub_date(world.doi, world.pub_event_type)
  #assert world.pub_date is not None, \
  #  "Got pub_date %s" % world.pub_date
  
@step(u'I get the date string from the pub date')
def i_get_the_date_string_from_the_pub_date(step):
  if world.pub_date is None:
    world.date_string = None
  else:
    world.date_string = time.strftime(world.date_format, world.pub_date)
    assert world.date_string is not None, \
      "Got date_string %s" % world.date_string
  
@step(u'I get the date string (.*)')
def i_get_the_date_string(step, date_string):
  if date_string == "None": date_string = None
  assert world.date_string == date_string, \
    "Got date_string %s" % world.date_string

@step(u'I have an s3 key name (.*)')
def i_have_an_s3_key_name_s3_key_name(step, s3_key_name):
  world.s3_key_name = s3_key_name
  assert world.s3_key_name is not None, \
    "Got s3_key_name %s" % world.s3_key_name
    
@step(u'I have the prefix (\S+)')
def i_have_the_prefix_prefix(step, prefix):
  world.prefix = prefix
  assert world.prefix is not None, \
    "Got prefix %s" % world.prefix
    
@step(u'I get doi id from poa s3 key name using the article provider')
def i_get_doi_id_from_poa_s3_key_name_using_the_article_provider(step):
  world.doi_id = world.article.get_doi_id_from_poa_s3_key_name(world.s3_key_name)
  assert world.doi_id is not None, \
    "Got doi_id %s" % world.doi_id
    
@step(u'I get doi id from s3 key name using the article provider')
def i_get_doi_id_from_s3_key_name_using_the_article_provider(step):
  world.doi_id = world.article.get_doi_id_from_s3_key_name(world.s3_key_name)
  assert world.doi_id is not None, \
    "Got doi_id %s" % world.doi_id
    
@step(u'I get doi_id (\d+)')
def i_get_doi_id_doi_id(step, doi_id):
  assert world.doi_id == int(doi_id), \
    "Got doi_id %s" % world.doi_id
