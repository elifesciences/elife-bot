from lettuce import *
import activity
import json

@step('I get a setting for postfix (\S+)')
def get_a_setting_for_postfix(step, postfix):
  ident = eval("world.settings." + postfix)
  world.postfix = ident
  assert world.postfix is not None, \
    "Got setting postfix %s" % world.postfix
    
@step('I have imported the SimpleDB provider module')
def import_simpledb_provider_module(step):
  imported = None
  try:
    import provider.simpleDB as dblib
    world.db = dblib.SimpleDB(world.settings)
    imported = True
  except:
    imported = False
  assert imported is True, \
    "SimpleDB module was imported"
    
@step('I get the domain name from the SimpleDB provider for (\S+)')
def get_the_domain_name_from_the_simpledb_provider_for_domain(step, domain):
  world.domain = domain
  world.domain_name = world.db.get_domain_name(domain)
  assert world.domain_name is not None, \
    "Got domain_name %s" % world.domain_name

@step('I have a domain name equal to the domain plus the postfix')
def i_have_a_domain_name_equal_to_the_domain_plus_the_postfix(step):
  domain_name_concatenation = world.domain + world.postfix
  assert world.domain_name == domain_name_concatenation, \
    "Got domain name plus the postfix %s" % domain_name_concatenation

@step('I have the domain name (\S+)')
def i_have_the_domain_name(step, domain_name):
  world.domain_name = domain_name
  assert world.domain_name is not None, \
    "Got domain name %s" % world.domain_name

@step('I have the file data types (.*)')
def i_have_the_file_data_types(step, file_data_types):
  world.file_data_types = json.loads(file_data_types)
  assert world.file_data_types is not None, \
    "Got file data types %s" % json.dumps(world.file_data_types)

@step('I have the date format (\S+)')
def i_have_the_date_format(step, date_format):
  world.date_format = date_format
  assert world.date_format is not None, \
    "Got date format %s" % world.date_format

@step('And I have the bucket name (\S+)')
def i_have_the_bucket_name(step, bucket_name):
  if(bucket_name == "None"):
    world.bucket_name = None
    assert world.bucket_name is None, \
      "Got bucket name %s" % world.bucket_name
  else:
    world.bucket_name = bucket_name
    assert world.bucket_name is not None, \
      "Got bucket name %s" % world.bucket_name

@step('I have the file data type (\S+)')
def i_have_the_file_data_type(step, file_data_type):
  if(file_data_type == "None"):
    world.file_data_type = None
    assert world.file_data_type is None, \
      "Got file data type %s" % world.file_data_type
  else:
    world.file_data_type = file_data_type
    assert world.file_data_type is not None, \
      "Got file data type %s" % world.file_data_type

@step('I have the doi id (\S+)')
def i_have_the_doi_id(step, doi_id):
  if(doi_id == "None"):
    world.doi_id = None
    assert world.doi_id is None, \
      "Got doi id %s" % world.doi_id
  else:
    world.doi_id = doi_id
    assert world.doi_id is not None, \
      "Got doi id %s" % world.doi_id

@step('I have the last updated since (\S+)')
def i_have_the_last_updated_since(step, last_updated_since):
  if(last_updated_since == "None"):
    world.last_updated_since = None
    assert world.last_updated_since is None, \
      "Got last updated since %s" % world.last_updated_since
  else:
    world.last_updated_since = last_updated_since
    assert world.last_updated_since is not None, \
      "Got last updated since %s" % world.last_updated_since
    
@step('I have the latest value (\S+)')
def i_have_the_latest_value(step, latest):
  if(latest == "None"):
    world.latest = None
    assert world.latest is None, \
      "Got latest %s" % world.latest
  else:
    world.latest = latest
    assert world.latest is not None, \
      "Got latest %s" % world.latest

@step('I get the query from the SimpleDB provider')
def i_get_the_query_from_the_simpledb_provider(step):
  world.query = world.db.elife_get_article_S3_query(
    date_format = world.date_format,
    domain_name = world.domain_name,
    file_data_types = world.file_data_types,
    bucket_name = world.bucket_name,
    file_data_type = world.file_data_type,
    doi_id = world.doi_id,
    last_updated_since = world.last_updated_since)
  assert world.query is not None, \
    "Got query %s" % world.query

@step('I have the SimpleDB query (.*)')
def i_have_the_simpledb_query(step, query):
  assert world.query == query, \
    "Got query %s" % world.query
  
@step('I have a document (\S+)')
def have_a_document(step, document):
  world.document = document
  assert world.document is not None, \
    "Got document %s" % world.document
  
@step('I get the latest article S3 files from SimpleDB')
def i_get_the_latest_article_s3_files_from_simpledb(step):
  world.item_list = world.db.elife_filter_latest_article_S3_file_items(world.json, world.file_data_types)
  assert world.item_list is not None, \
    "Got item list %s" % world.item_list
  
@step('I have an item list count (\d+)')
def then_i_have_an_item_list_count(step, count):
  assert len(world.item_list) == int(count), \
    "Got count %s" % len(world.item_list)
  
@step('the item list (\d+) (\S+) is (.*)')
def and_the_item_list_index_key_is_value(step, index, key, value):
  index = int(index)
  key = str(key)
  try:
    match_value = world.item_list[index][key]
  except KeyError:
    match_value = None
  assert match_value == value, \
    "Got value %s" % match_value