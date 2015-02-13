from lettuce import *
import activity
import json
import datetime
import os
import provider.templates as templateslib

@step('I create a templates provider')
def i_create_a_templates_provider(step):
  try:
    world.settings = world.settings
  except AttributeError:
    world.settings = None

  world.templates = templateslib.Templates(world.settings, world.tmp_dir)
  assert world.templates is not None, \
    "Got templates %s" % world.templates
    
@step('I get a filesystem provider from the templates provider')
def get_the_filesystem_provider_from_the_templates_provider(step):
  world.fs = world.templates.get_fs()
  assert world.fs is not None, \
    "Got filesystem provider %s" % world.fs

@step('I have the template name (\S+)')
def i_have_the_template_name_template_name(step, template_name):
  world.template_name = template_name
  assert world.template_name is not None, \
    "Got template_name %s" % world.template_name
    
@step('I read the document to content')
def i_read_the_document_to_content(step):
  f = open(world.document)
  world.content = f.read()
  f.close()
  assert world.content is not None, \
    "Got content %s" % world.content

@step('I save template contents to tmp dir with templates provider')
def i_save_template_contents_to_tmp_dir_with_templates_provider(step):
  world.templates.save_template_contents_to_tmp_dir(world.template_name, world.content)
  assert world.fs.document is not None, \
    "Got document %s" % world.fs.document
  
@step('I have the world filesystem document (\S+)')
def i_have_the_world_filesystem_document(step, filesystem_document):
  assert world.fs.document == filesystem_document, \
    "Got document %s" % world.fs.document

@step('I have a base directory (\S+)')
def i_have_a_base_directory(step, base_dir):
  world.base_dir = base_dir
  assert world.base_dir is not None, \
    "Got base_dir %s" % world.base_dir
  
@step('I get email templates list from the template provider')
def i_get_email_templates_list_from_the_template_provider(step):
  world.templates_list = world.templates.get_email_templates_list()
  assert world.templates_list is not None, \
    "Got templates_list %s" % world.templates_list

@step('I read each base dir plus templates list document to content')
def i_read_each_base_dir_plus_templates_list_document_to_content(step):
  template_count = 0
  for template_name in world.templates_list:
    filename = world.base_dir + template_name
    f = open(filename)
    content = f.read()
    f.close()
    world.templates.save_template_contents_to_tmp_dir(template_name, content)
    template_count = template_count + 1
  assert len(world.templates_list) == template_count, \
    "Processed %s of %s templates" % (template_count, len(world.templates_list))
  
@step('I set the templates provider email templates warmed to True')
def i_set_the_templates_provider_email_templates_warmed_to_true(step):
  world.templates.email_templates_warmed = True
  assert world.templates.email_templates_warmed is True, \
    "Got email_templates_warmed %s" % world.templates.email_templates_warmed
  
@step('I have the author json (.+)')
def i_have_the_author(step, author_json):
  world.author = json.loads(author_json)
  assert world.author is not None, \
    "Got author %s" % world.author

@step('I have the article json (.+)')
def i_have_the_article(step, article_json):
  world.article = json.loads(article_json)
  assert world.article is not None, \
    "Got article %s" % world.article

@step('I have the elife json (.+)')
def i_have_the_elife(step, elife_json):
  world.elife = json.loads(elife_json)
  assert world.elife is not None, \
    "Got elife %s" % world.elife

@step('I get author publication email body from the templates provider')
def i_get_author_publication_email_body_from_the_templates_provider(step):
  world.email_body = world.templates.get_author_publication_email_body(world.author, world.article)
  assert world.email_body is not None, \
    "Got email_body %s" % world.email_body
    
@step('I have the email body (.+)')
def i_have_the_email_body_email_body(step, email_body):
  email_body_newline_replaced = world.email_body.replace("\n", "\\n")
  assert email_body_newline_replaced == email_body, \
    "Got email_body %s" % email_body_newline_replaced
