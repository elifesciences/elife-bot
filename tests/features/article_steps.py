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
    
@step('I get a doi id from the article provider (\S+)')
def i_get_a_doi_id_from_the_article_provider_doi_id(step, doi_id):
  world.doi_id = world.article.get_doi_id(world.doi)
  assert world.doi_id == doi_id, \
  "Got article_doi_id %s" % world.doi_id

@step('I get a DOI url from the article provider (\S+)')
def i_get_a_doi_url_from_the_article_provider(step, doi_url):
  world.doi_url = world.article.get_doi_url(world.doi)
  assert world.doi_url == doi_url, \
  "Got doi_url %s" % world.doi_url

@step('I get a lens url from the article provider (\S+)')
def i_get_a_lens_url_from_the_article_provider(step, lens_url):
  world.lens_url = world.article.get_lens_url(world.doi)
  assert world.lens_url == lens_url, \
  "Got lens_url %s" % world.lens_url
  
@step('I get a tweet url from the article provider (\S+)')
def i_get_a_tweet_url_from_the_article_provider(step, tweet_url):
  world.tweet_url = world.article.get_tweet_url(world.doi)
  assert world.tweet_url == tweet_url, \
  "Got tweet_url %s" % world.tweet_url
  
@step('I parse the document with the article provider')
def i_parse_the_document_with_the_article_provider(step):
  world.parsed = world.article.parse_article_file(world.document_name)
  assert world.parsed is True, \
    "Got parsed %s" % world.parsed
    
@step('I have the article doi (\S+)')
def i_have_the_article_doi(step, doi):
  assert world.article.doi == doi, \
  "Got doi %s" % world.article.doi 
  
@step('I have the article doi_id (\S+)')
def i_have_the_article_doi_id(step, doi_id):
  assert world.article.doi_id == doi_id, \
  "Got doi_id %s" % world.article.doi_id 
    
@step('I have the article doi_url (\S+)')
def i_have_the_article_doi_url(step, doi_url):
  assert world.article.doi_url == doi_url, \
  "Got doi_url %s" % world.article.doi_url 
    
@step('I have the article lens_url (\S+)')
def i_have_the_article_lens_url(step, lens_url):
  assert world.article.lens_url == lens_url, \
  "Got lens_url %s" % world.article.lens_url 
    
@step('I have the article tweet_url (\S+)')
def i_have_the_article_tweet_url(step, tweet_url):
  assert world.article.tweet_url == tweet_url, \
  "Got tweet_url %s" % world.article.tweet_url 

@step('I have the article pub_date_timestamp (\S+)')
def i_have_the_article_pub_date_timestamp(step, pub_date_timestamp):
  # Possible there is no pub date
  if hasattr(world.article, "pub_date_timestamp"):
    if pub_date_timestamp == "None":
      assert world.article.pub_date_timestamp is None, \
        "Got pub_date_timestamp %s" % world.article.pub_date_timestamp
    else:
      assert int(world.article.pub_date_timestamp) == int(pub_date_timestamp), \
        "Got pub_date_timestamp %s" % world.article.pub_date_timestamp
  else:
    # Using None as the value to compare when there is no pub_date_timestamp
    assert pub_date_timestamp is None, \
    "Got pub_date_timestamp %s" % world.article.pub_date_timestamp

@step('I have the article article_type (\S+)')
def i_have_the_article_article_type(step, article_type):
  assert world.article.article_type == article_type, \
  "Got article_type %s" % world.article.article_type

@step(u'I count the total related articles as (\d+)')
def i_count_the_total_related_articles_as(step, number):
  count = len(world.article.related_articles)
  assert count == int(number), \
  "Got related_articles count %d" % count
  
@step(u'I have the article related article index (\d+) xlink_href (\S+)')
def i_have_the_article_related_article_index_index_xlink_href(step, index, xlink_href):
  
  if xlink_href == "None":
    # If value to test is None then check length of array is 0 just to be sure
    assert len(world.article.related_articles) == 0, \
    "Got a non-None value for the related articles"
  else:
    href = world.article.related_articles[int(index)]["xlink_href"]
    assert xlink_href == href, \
    "Got xlink_href %s" % href

@step(u'I have the article is poa (\S+)')
def i_have_the_article_is_poa(step, is_poa):
  # Allow boolean or None comparison
  if is_poa == "True": is_poa = True
  if is_poa == "False": is_poa = False
  if is_poa == "None": is_poa = None
      
  assert world.article.is_poa == is_poa, \
  "Got is_poa %s" % world.article.is_poa

@step(u'I have the article related insight doi (\S+)')
def i_have_the_article_related_insight_doi(step, insight_doi):
  if insight_doi == "None":
    insight_doi = None

  related_insight_doi = world.article.get_article_related_insight_doi()
  assert insight_doi == related_insight_doi, \
  "Got related_insight_doi %s" % related_insight_doi
  
@step(u'I get article lookup url with the article provider')
def i_get_article_lookup_url_with_the_article_provider(step):
  world.lookup_url = world.article.get_article_lookup_url(world.doi_id)
  assert world.lookup_url is not None, \
    "Got lookup_url %s" % world.lookup_url
    
@step(u'I have lookup url (\S+)')
def i_have_lookup_url_lookup_url(step, lookup_url):
  assert world.lookup_url == lookup_url, \
  "Got world.lookup_url %s" % world.lookup_url
    
@step(u'I have is poa (\S+)')
def i_have_is_poa(step, is_poa):
  if is_poa == "True":  world.is_poa = True
  if is_poa == "False": world.is_poa = False
  assert world.is_poa is not None, \
    "Got is_poa %s" % world.is_poa
    
@step(u'I have was ever poa (\S+)')
def i_have_was_ever_poa(step, was_ever_poa):
  if was_ever_poa == "None":
    world.was_ever_poa = None
    assert world.was_ever_poa is None, \
      "Got was_ever_poa %s" % world.was_ever_poa
  else:
    if was_ever_poa == "True":  world.was_ever_poa = True
    if was_ever_poa == "False": world.was_ever_poa = False
    assert world.was_ever_poa is not None, \
      "Got was_ever_poa %s" % world.was_ever_poa
    
@step(u'I have the article url (\S+)')
def i_have_the_article_url(step, article_url):
  world.article_url = article_url
  assert world.article_url is not None, \
    "Got article_url %s" % world.article_url
    
@step(u'I check is article published with the article provider')
def i_check_is_article_published_with_the_article_provider(step):
  world.is_published = world.article.check_is_article_published(
    world.doi,
    world.is_poa,
    world.was_ever_poa,
    world.article_url)
  assert world.is_published is not None, \
    "Got is_published %s" % world.is_published
    
@step(u'I have is published (\S+)')
def i_have_is_published(step, is_published):
  assert str(world.is_published) == is_published, \
    "Got is_published %s" % world.is_published
  
@step(u'I have the article authors string (.*)')
def i_have_the_article_authors_string_authors_string(step, authors_string):
  assert world.article.authors_string == authors_string, \
    "Got authors_string %s" % world.article.authors_string
  
@step(u'I have the article is in display channel "([^"]*)" (\S+)')
def i_have_the_article_is_in_display_channel_group(step, display_channel_name, is_in_display_channel):
  if is_in_display_channel == "True":  is_in_display_channel = True
  if is_in_display_channel == "False": is_in_display_channel = False
  
  is_in = world.article.is_in_display_channel(display_channel_name)
  assert is_in == is_in_display_channel, \
    "Got is_in_display_channel %s" % is_in

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
  
@step(u'I get date string from s3 key name using the article provider')
def i_get_date_string_from_s3_key_name_using_the_article_provider(step):
  world.date_string = world.article.get_date_string_from_s3_key_name(world.s3_key_name, world.prefix)
  assert world.date_string is not None, \
    "Got date_string %s" % world.date_string
    
