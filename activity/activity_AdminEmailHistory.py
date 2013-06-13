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
AdminEmailHistory activity
"""

class activity_AdminEmailHistory(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "AdminEmailHistory"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Email administrators a workflow history status message."
    
  def do_activity(self, data = None):
    """
    AdminEmailHistory activity, do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
      
    ses_conn = conn = boto.ses.connect_to_region(self.settings.simpledb_region, aws_access_key_id = self.settings.aws_access_key_id, aws_secret_access_key = self.settings.aws_secret_access_key)
    
    # Note: Create a verified sender email address, only done once
    #conn.verify_email_address(self.settings.ses_sender_email)
  
    date_format = '%Y-%m-%dT%H:%M:%S.000Z'
    datetime_string = time.strftime(date_format, time.gmtime())

    time_period = 60*60*4
    history_text = self.get_workflow_count_by_closestatus(time_period)

    sender_email = self.settings.ses_sender_email
    recipient_email = self.settings.ses_admin_email
    subject = "eLife SWF workflow history " + datetime_string
    body = "A short history of workflow executions\n"
    body += "As at " + datetime_string + "\n"
    body += "Time period: " + str(time_period) + " seconds" + "\n"
    body += "Domain: " + self.settings.domain + "\n"
    body = body + history_text
    body = body + "\n\nSincerely\n\neLife bot"
    format = "text"
    
    ses_conn.send_email(
      source       = sender_email,
      to_addresses = recipient_email,
      subject      = subject,
      body         = body,
      format       = format)
    
    return True

  def get_workflow_count_by_closestatus(self, seconds):
    
    history_text = ""
    
    close_status_list = ["COMPLETED", "FAILED", "CANCELED", "TERMINATED", "CONTINUED_AS_NEW", "TIMED_OUT"]
    
    swfmeta = swfmetalib.SWFMeta(self.settings)
    swfmeta.connect()

    date_format = '%Y-%m-%dT%H:%M:%S.000Z'
    current_timestamp = calendar.timegm(time.gmtime())
    
    start_latest_date_timestamp = current_timestamp
    start_oldest_date_timestamp = start_latest_date_timestamp - seconds
    
    for close_status in close_status_list:
      count = swfmeta.get_closed_workflow_execution_count(
        domain            = self.settings.domain,
        start_oldest_date = start_oldest_date_timestamp,
        start_latest_date = start_latest_date_timestamp,
        close_status      = close_status
        )
      run_count = None
      try:
        run_count = count["count"]
      except:
        run_count = None
        
      # Concatenate the message
      history_text = history_text + "\n" + close_status + ": " + str(run_count)
      
    return history_text
