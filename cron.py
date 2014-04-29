import json
import random
import datetime
import calendar
import time
import importlib
from optparse import OptionParser

import settings as settingsLib

import boto.swf

import provider.swfmeta as swfmetalib
import starter

"""
SWF cron
"""

def run_cron(ENV = "dev"):
  # Specify run environment settings
  settings = settingsLib.get_settings(ENV)
  
  current_time = time.gmtime()
  
  # Based on the minutes of the current time, run certain starters
  if(current_time.tm_min >= 0 and current_time.tm_min <= 59):
    # Jobs to start at any time during the hour

    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_FiveMinute",
      workflow_id   = "cron_FiveMinute",
      start_seconds = 60*3)
  
  # Based on the minutes of the current time, run certain starters
  if(current_time.tm_min >= 0 and current_time.tm_min <= 29):
    # Jobs to start at the top of the hour
    #print "Top of the hour"

    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "starter_S3Monitor",
      workflow_id   = "S3Monitor",
      start_seconds = 60*31)
    
    pass
  
  elif(current_time.tm_min >= 30 and current_time.tm_min <= 59):
    # Jobs to start at the bottom of the hour
    #print "Bottom of the hour"
    
    # POA bucket polling
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "starter_S3Monitor",
      workflow_id   = "S3Monitor_POA",
      start_seconds = 60*31)
    
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_NewS3XML",
      workflow_id   = "cron_NewS3XML",
      start_seconds = 60*31)
    
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_NewS3PDF",
      workflow_id   = "cron_NewS3PDF",
      start_seconds = 60*31)
    
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_NewS3SVG",
      workflow_id   = "cron_NewS3SVG",
      start_seconds = 60*31)
    
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_NewS3Suppl",
      workflow_id   = "cron_NewS3Suppl",
      start_seconds = 60*31)
    
    workflow_conditional_start(
      ENV           = ENV,
      starter_name  = "cron_NewS3JPG",
      workflow_id   = "cron_NewS3JPG",
      start_seconds = 60*31)
    
    if(current_time.tm_min >= 45 and current_time.tm_min <= 59):
      # Bottom quarter of the hour
      
      workflow_conditional_start(
        ENV           = ENV,
        starter_name  = "starter_AdminEmail",
        workflow_id   = "AdminEmail",
        start_seconds = (60*60*4)-(14*60))

def workflow_conditional_start(ENV, starter_name, start_seconds, data = None, workflow_id = None, workflow_name = None, workflow_version = None):
  """
  Given workflow criteria, check the workflow completion history for the last time run
  If it last run more than start_seconds ago, start a new workflow
  """
  
  diff_seconds = None
  last_startTimestamp = None
  
  settings = settingsLib.get_settings(ENV)
  
  swfmeta = swfmetalib.SWFMeta(settings)
  swfmeta.connect()
  
  last_startTimestamp = swfmeta.get_last_completed_workflow_execution_startTimestamp(workflow_id = workflow_id, workflow_name = workflow_name, workflow_version = workflow_version)
  
  current_timestamp = calendar.timegm(time.gmtime())
  
  if(last_startTimestamp is not None):
    diff_seconds = current_timestamp - start_seconds - last_startTimestamp
    print diff_seconds
  
  if(diff_seconds >= 0 or last_startTimestamp is None):
    # Start a new workflow
    # Load the starter module
    module_name = "starter." + starter_name
    importlib.import_module(module_name)
    full_path = "starter." + starter_name + "." + starter_name + "()"
    s = eval(full_path)
    
    # Customised start functions
    if(starter_name == "starter_S3Monitor"):
      
      if workflow_id == "S3Monitor":
        s.start(ENV = ENV, workflow = "S3Monitor")
      if workflow_id == "S3Monitor_POA":
        s.start(ENV = ENV, workflow = "S3Monitor_POA")
        
    elif(starter_name == "starter_AdminEmail"):
      s.start(ENV = ENV, workflow = "AdminEmail")
      
    elif(starter_name == "cron_NewS3XML"
      or starter_name == "cron_NewS3PDF"
      or starter_name == "cron_NewS3SVG"
      or starter_name == "cron_FiveMinute"
      or starter_name == "cron_NewS3Suppl"
      or starter_name == "cron_NewS3JPG"
      ):
      s.start(ENV = ENV)
  
if __name__ == "__main__":

  # Add options
  parser = OptionParser()
  parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
  (options, args) = parser.parse_args()
  if options.env: 
    ENV = options.env

  run_cron(ENV)
