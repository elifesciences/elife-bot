from lettuce import *
import activity
import json

@step('I convert the document name from path to jpg filename using the activity object')
def i_convert_the_document_name_from_path_to_jpg_filename_using_the_activity_object(step):
    world.document_name_from_path = world.activity_object.get_jpg_filename(world.document_name_from_path)
    assert world.document_name_from_path is not None, \
        "Got document_name_from_path %s" % world.document_name_from_path

@step('I can get a domain from the activity')
def get_domain_from_activity_object(step):
    assert world.activity_object.domain is not None, \
        "Got domain %s" % world.activity_object.domain
    
@step('I can get a task_list from the activity')
def get_task_list_from_activity_object(step):
    assert world.activity_object.task_list is not None, \
        "Got task_list %s" % world.activity_object.task_list
    
@step('I get the activity name (\S+)')
def get_activity_name(step, name):
    assert world.activity_object.name == name, \
        "Got name %s" % world.activity_object.name

@step('I get a result from the activity')
def get_result_from_activity_object(step):
    world.result = world.activity_object.do_activity(world.json)
    assert world.result is not None, \
        "Got result %s" % world.result
    
@step('I can get a domain from the workflow')
def get_domain_from_workflow_object(step):
    assert world.workflow_object.domain is not None, \
        "Got domain %s" % world.workflow_object.domain
    
@step('I can get a task_list from the workflow')
def get_task_list_from_workflow_object(step):
    assert world.workflow_object.task_list is not None, \
        "Got task_list %s" % world.workflow_object.task_list
    
@step('I get the workflow name (\S+)')
def get_workflow_name(step, name):
    assert world.workflow_object.name == name, \
        "Got name %s" % world.workflow_object.name
    
@step('I have the document name (\S+)')
def have_the_document_name(step, document_name):
    world.document_name = document_name
    assert world.document_name is not None, \
        "Got document %s" % world.document_name 

@step('I have the filename (\S+)')
def have_the_filename(step, filename):
    if(filename == "None"):
        world.filename = None
        assert world.filename is None, \
            "Got filename %s" % world.filename 
    else:
        world.filename = filename
        assert world.filename is not None, \
            "Got filename %s" % world.filename 
    
@step('I have the item name (\S+)')
def have_the_item_name(step, item_name):
    world.item_name = item_name
    assert world.item_name is not None, \
        "Got item name %s" % world.item_name
    
@step('I have the item attr last_modified_timestamp (\S+)')
def have_the_item_attr_last_modified_timestamp(step, last_modified_timestamp):
    world.item_attrs = {}
    # Convert string to int to replicate real running action
    world.item_attrs['last_modified_timestamp'] = int(last_modified_timestamp)
    assert world.item_attrs is not None, \
        "Got item attributes %s" % world.item_attrs
    
@step('I get the log_item_name from the S3Monitor (\S+)')
def get_the_log_item_name_from_the_s3monitor(step, log_item_name):
    world.log_item_name = world.activity_object.get_log_item_name(world.item_name, world.item_attrs)
    assert world.log_item_name == log_item_name, \
        "Got log_item_name %s" % world.log_item_name

@step('I have the base name (\S+)')
def have_the_base_name(step, base_name):
    world.base_name = base_name
    assert world.base_name is not None, \
        "Got base_name %s" % world.base_name

@step('I have the timestamp (\S+)')
def have_the_timestamp(step, timestamp):
    if(timestamp == "None"):
        world.timestamp = None
        assert world.timestamp is None, \
            "Got timestamp %s" % world.timestamp
    else:
        # Takes a float, apparently
        world.timestamp = float(timestamp)
        assert world.timestamp is not None, \
            "Got timestamp %f" % world.timestamp

@step('I have the date format (\S+)')
def have_the_date_format(step, date_format):
    world.date_format = date_format
    assert world.date_format is not None, \
        "Got date_format %s" % world.date_format

@step('I get the expanded date attributes from S3Monitor using a timestamp')
def get_the_expanded_date_attributes_from_S3Monitor_using_a_timestamp(step):
    world.date_attrs = world.activity_object.get_expanded_date_attributes(world.base_name, world.date_format, world.timestamp)
    assert world.date_attrs is not None, \
        "Got date_attrs %s" % world.date_attrs

@step('I have the timestamp attribute (\S+)')
def have_the_timestamp_attribute(step, timestamp):
    key_name = world.base_name + '_timestamp'
    assert world.date_attrs[key_name] == float(timestamp), \
        "Got timestamp %s" % world.date_attrs[key_name]
    
@step('I have the date attribute (\S+)')
def have_the_date_attribute(step, date):
    key_name = world.base_name + '_date'
    assert world.date_attrs[key_name] == date, \
        "Got date %s" % world.date_attrs[key_name]
    
@step('I have the year attribute (\S+)')
def have_the_year_attribute(step, year):
    key_name = world.base_name + '_year'
    assert world.date_attrs[key_name] == year, \
        "Got date %s" % world.date_attrs[key_name]
    
@step('I have the month attribute (\S+)')
def have_the_month_attribute(step, month):
    key_name = world.base_name + '_month'
    assert world.date_attrs[key_name] == month, \
        "Got date %s" % world.date_attrs[key_name]
    
@step('I have the day attribute (\S+)')
def have_the_day_attribute(step, day):
    key_name = world.base_name + '_day'
    assert world.date_attrs[key_name] == day, \
        "Got date %s" % world.date_attrs[key_name]
    
@step('I have the time attribute (\S+)')
def have_the_time_attribute(step, time):
    key_name = world.base_name + '_time'
    assert world.date_attrs[key_name] == time, \
        "Got time %s" % world.date_attrs[key_name]
    
@step('I get a filesystem provider from the activity object')
def get_the_filesystem_provider_from_the_activity_object(step):
    world.fs = world.activity_object.get_fs()
    assert world.fs is not None, \
        "Got filesystem provider %s" % world.fs
    
@step('I have the elife_id (\S+)')
def have_the_elife_id_elife_id(step, elife_id):
    world.elife_id = elife_id
    assert world.elife_id is not None, \
        "Got elife_id %s" % world.elife_id

@step('I read document to content with the activity object')
def read_document_to_content_with_the_activity_object(step):
    #try:
    #    world.filename = world.filename
    #except AttributeError:
    world.filename = None
    world.content = world.activity_object.read_document_to_content(world.document_name, world.filename)
    content_present = False
    if(world.content is not None):
        content_present = True
    assert content_present, \
        "Got content_present %s" % content_present

@step('I get the document from the activity object')
@step('I get the document path from the activity object')
def get_the_document_from_the_activity_object(step):
    world.document_path = world.activity_object.get_document()
    assert world.document_path is not None, \
        "Got document_path %s" % world.document_path

@step('I set the document as list index (\d+)')
def set_the_document_as_list_index(step, index):
    world.document_path = world.document_path[int(index)]
    assert world.document_path is not None, \
        "Got document_path %s" % world.document_path

@step('And I get the document name from path using the activity object')
def get_the_document_name_from_path_using_the_activity_object(step):
    world.document_name_from_path = world.activity_object.get_document_name_from_path(world.document_path)
    assert world.document_name_from_path is not None, \
        "Got document_name_from_path %s" % world.document_name_from_path

@step('I get the pdf object S3key name from the activity object')
def get_the_pdf_object_s3key_name_from_the_activity_object(step):
    world.S3key_name = world.activity_object.get_pdf_object_S3key_name(world.elife_id, world.document_name_from_path)
    assert world.S3key_name is not None, \
        "Got S3key_name %s" % world.S3key_name

@step('I get the svg object S3key name from the activity object')
def get_the_svg_object_s3key_name_from_the_activity_object(step):
    world.S3key_name = world.activity_object.get_svg_object_S3key_name(world.elife_id, world.document_name_from_path)
    assert world.S3key_name is not None, \
        "Got S3key_name %s" % world.S3key_name
    
@step('I get the suppl object S3key name from the activity object')
def get_the_suppl_object_s3key_name_from_the_activity_object(step):
    world.S3key_name = world.activity_object.get_suppl_object_S3key_name(world.elife_id, world.document_name_from_path)
    assert world.S3key_name is not None, \
        "Got S3key_name %s" % world.S3key_name
    
@step('I get the jpg object S3key name from the activity object')
def get_the_jpg_object_s3key_name_from_the_activity_object(step):
    world.S3key_name = world.activity_object.get_jpg_object_S3key_name(world.elife_id, world.document_name_from_path)
    assert world.S3key_name is not None, \
        "Got S3key_name %s" % world.S3key_name
    
@step('I have the S3key_name (\S+)')
def have_the_s3key_name_s3key_name(step, S3key_name):
    assert world.S3key_name == S3key_name, \
        "Got S3key_name %s" % world.S3key_name
    
@step('I get authors from the activity object')
def i_get_authors_from_the_activity_object(step):
    world.authors = world.activity_object.get_authors(document = world.document)
    assert world.authors is not None, \
        "Got authors %s" % json.dumps(world.authors)
    
@step('I get editors from the activity object')
def i_get_editors_from_the_activity_object(step):
    world.editors = world.activity_object.get_editors(document = world.document)
    assert world.editors is not None, \
        "Got editors %s" % json.dumps(world.editors)
