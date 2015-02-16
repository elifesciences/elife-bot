from lettuce import *
import activity
import json
import datetime
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

@step('I have the article pub_date_timestamp (\d+)')
def i_have_the_article_pub_date_timestamp(step, pub_date_timestamp):
  assert int(world.article.pub_date_timestamp) == int(pub_date_timestamp), \
  "Got pub_date_timestamp %s" % world.article.pub_date_timestamp 

@step('I have the article article_type (\S+)')
def i_have_the_article_article_type(step, article_type):
  assert world.article.article_type == article_type, \
  "Got article_type %s" % world.article.article_type