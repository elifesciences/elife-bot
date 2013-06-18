import boto.swf
import json
import random
import datetime
import calendar
import time

import activity

import boto.ses

import provider.swfmeta as swfmetalib

"""
WorkflowConflictCheck activity
"""

class activity_WorkflowConflictCheck(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "WorkflowConflictCheck"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*30
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*30
    self.description = "Check for open workflows to determine logical conflicts, when two workflow types should not run concurrently."
    
  def do_activity(self, data = None):
    """
    WorkflowConflictCheck activity, do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    is_open = None
    
    workflow_id = None
    workflow_name = None
    workflow_version = None
    
    try:
      workflow_id = data["data"]["workflow_id"]
    except KeyError:
      pass
    try:
      workflow_name = data["data"]["workflow_name"]
    except KeyError:
      pass
    try:
      workflow_version = data["data"]["workflow_version"]
    except KeyError:
      pass
    
    swfmeta = swfmetalib.SWFMeta(self.settings)
    swfmeta.connect()
    is_open = swfmeta.is_workflow_open(workflow_id = workflow_id, workflow_name = workflow_name, workflow_version = workflow_version)
    
    # Return logic: if is_open is False, then return True as being no conflict
    #  But, if is_open is True, do not return a value, causing this activity to timeout
    if is_open is False:
      return True
    else:
      return None
