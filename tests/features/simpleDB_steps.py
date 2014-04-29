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

@step('I have the sent status (\S+)')
def i_have_the_sent_status(step, sent_status):
  if(sent_status == "None"):
    world.sent_status = None
    assert world.sent_status is None, \
      "Got sent_status %s" % world.sent_status
  else:
    world.sent_status = sent_status
    assert world.sent_status is not None, \
      "Got sent_status %s" % world.sent_status
    
@step('I have the email type (\S+)')
def i_have_the_email_type(step, email_type):
  if(email_type == "None"):
    world.email_type = None
    assert world.email_type is None, \
      "Got email_type %s" % world.email_type
  else:
    world.email_type = email_type
    assert world.email_type is not None, \
      "Got email_type %s" % world.email_type
      
@step('I have the date scheduled before (\S+)')
def i_have_the_date_scheduled_before(step, date_scheduled_before):
  if(date_scheduled_before == "None"):
    world.date_scheduled_before = None
    assert world.date_scheduled_before is None, \
      "Got date_scheduled_before %s" % world.date_scheduled_before
  else:
    world.date_scheduled_before = date_scheduled_before
    assert world.date_scheduled_before is not None, \
      "Got date_scheduled_before %s" % world.date_scheduled_before

@step('I have the date sent before (\S+)')
def i_have_the_date_sent_before(step, date_sent_before):
  if(date_sent_before == "None"):
    world.date_sent_before = None
    assert world.date_sent_before is None, \
      "Got date_sent_before %s" % world.date_sent_before
  else:
    world.date_sent_before = date_sent_before
    assert world.date_sent_before is not None, \
      "Got date_sent_before %s" % world.date_sent_before

@step('I have the recipient email (\S+)')
def i_have_the_recipient_email(step, recipient_email):
  if(recipient_email == "None"):
    world.recipient_email = None
    assert world.recipient_email is None, \
      "Got recipient_email %s" % world.recipient_email
  else:
    world.recipient_email = recipient_email
    assert world.recipient_email is not None, \
      "Got recipient_email %s" % world.recipient_email

@step('I have the sort by (\S+)')
def i_have_the_sort_by(step, sort_by):
  if(sort_by == "None"):
    world.sort_by = None
    assert world.sort_by is None, \
      "Got sort_by %s" % world.sort_by
  else:
    world.sort_by = sort_by
    assert world.sort_by is not None, \
      "Got sort_by %s" % world.sort_by

@step('I have the limit (\S+)')
def i_have_the_limit(step, limit):
  if(limit == "None"):
    world.limit = None
    assert world.limit is None, \
      "Got limit %s" % world.limit
  else:
    world.limit = limit
    assert world.limit is not None, \
      "Got limit %s" % world.limit
    
@step('I have the check is unique (\S+)')
def i_have_the_check_is_unique(step, check_is_unique):
  if(check_is_unique == "None"):
    world.check_is_unique = None
    assert world.check_is_unique is None, \
      "Got check_is_unique %s" % world.check_is_unique
  else:
    world.check_is_unique = check_is_unique
    assert world.check_is_unique is not None, \
      "Got check_is_unique %s" % world.check_is_unique

@step('I have the query type (\S+)')
def i_have_the_query_type(step, query_type):
  if(query_type == "None"):
    world.query_type = None
    assert world.query_type is None, \
      "Got query_type %s" % world.query_type
  else:
    world.query_type = query_type
    assert world.query_type is not None, \
      "Got query_type %s" % world.query_type

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

@step('I get the email queue query from the SimpleDB provider')
def i_get_the_email_queue_query_from_the_simpledb_provider(step):
  world.query = world.db.elife_get_email_queue_query(
    date_format = world.date_format,
    domain_name = world.domain_name,
    query_type = world.query_type,
    sort_by = world.sort_by,
    limit = world.limit,
    sent_status = world.sent_status,
    email_type = world.email_type,
    doi_id = world.doi_id,
    date_scheduled_before = world.date_scheduled_before,
    date_sent_before = world.date_sent_before,
    recipient_email = world.recipient_email)
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

@step('I have the val (\S+)')
def i_have_the_val(step, val):
  world.val = val
  assert world.val is not None, \
    "Got val %s" % world.val

@step('I use SimpleDB to escape the val')
def i_use_simpledb_to_escape_the_val_val(step):
  world.escaped_val = world.db.escape(world.val)
  assert world.escaped_val is not None, \
    "Got escaped_val %s" % world.escaped_val
    
@step('I have the escaped val (\S+)')
def i_have_the_escaped_val_escaped_val(step, esc):
  assert world.escaped_val == str(esc), \
    "Got escaped_val %s" % world.escaped_val

@step('I get the unique email queue item_name from the SimpleDB provider')
def i_get_the_unique_email_queue_item_name_from_the_simpledb_provider(step):
  world.unique_item_name = world.db.elife_get_unique_email_queue_item_name(
    domain_name = str(world.domain_name),
    check_is_unique = world.check_is_unique,
    timestamp = world.timestamp,
    doi_id = world.doi_id,
    email_type = world.email_type,
    recipient_email = world.recipient_email)
  assert world.unique_item_name is not None, \
    "Got unique_item_name %s" % world.unique_item_name
  
@step('I have the unique item name (\S+)')
def i_have_the_unique_item_name(step, unique_item_name):
  assert world.unique_item_name == unique_item_name, \
    "Got unique_item_name %s" % len(world.unique_item_name)

@step('I connect to SimpleDB using the SimpleDB provider')
def i_connect_to_simpledb_using_the_simpledb_provider(step):
  world.sdb_conn = world.db.connect()
  assert world.sdb_conn is not None, \
    "Got sdb_conn %s" % world.sdb_conn
  
@step('I have the sender email (\S+)')
def i_have_the_sender_email(step, sender_email):
  world.sender_email = sender_email
  assert world.sender_email is not None, \
    "Got sender_email %s" % world.sender_email
  
@step('I have add value (\S+)')
def i_have_add_value(step, add):
  if(add == "None" or add == "False"):
    world.add = False
    assert world.add is False, \
      "Got add %s" % world.add
  elif(add == "True"):
    world.add = True
    assert world.add is True, \
      "Got add %s" % world.add
  else:
    world.add = add
    assert world.add is not None, \
      "Got add %s" % world.add
    
@step('I add email to email queue with the SimpleDB provider')
def i_add_email_to_email_queue_with_the_simpledb_provider(step):
  world.item_attrs = world.db.elife_add_email_to_email_queue(
    recipient_email = world.recipient_email,
    sender_email    = world.sender_email,
    email_type      = world.email_type,
    add             = world.add)
  assert world.item_attrs is not None, \
    "Got item_attrs %s" % json.dumps(world.item_attrs)
  
@step('I get item attributes date_scheduled_timestamp (\S+)')
def i_get_item_attributes_date_scheduled_timestamp(step, date_scheduled_timestamp):
  assert str(world.item_attrs["date_scheduled_timestamp"]) == date_scheduled_timestamp, \
    "Got date_scheduled_timestamp %s" % world.item_attrs["date_scheduled_timestamp"]
  
@step(u'I get the POA bucket query from the SimpleDB provider')
def i_get_the_poa_bucket_query_from_the_simpledb_provider(step):
  world.query = world.db.elife_get_POA_delivery_S3_query(
    date_format = world.date_format,
    domain_name = world.domain_name,
    bucket_name = world.bucket_name,
    last_updated_since = world.last_updated_since)
  assert world.query is not None, \
    "Got query %s" % world.query