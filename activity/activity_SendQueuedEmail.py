import boto.swf
import json
import random
import datetime
import calendar
import time

import activity

import boto.ses

import provider.simpleDB as dblib

"""
SendQueuedEmail activity
"""

class activity_SendQueuedEmail(activity.activity):
  
  def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
    activity.activity.__init__(self, settings, logger, conn, token, activity_task)

    self.name = "SendQueuedEmail"
    self.version = "1"
    self.default_task_heartbeat_timeout = 30
    self.default_task_schedule_to_close_timeout = 60*5
    self.default_task_schedule_to_start_timeout = 30
    self.default_task_start_to_close_timeout= 60*5
    self.description = "Send email in the email queue."
    
    # Data provider
    self.db = dblib.SimpleDB(settings)
    
    # Default limit of emails per activity
    self.limit = 100
    
  def do_activity(self, data = None):
    """
    SendQueuedEmail activity, do the work
    """
    if(self.logger):
      self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
    
    # Note: Create a verified sender email address, only done once
    #conn.verify_email_address(self.settings.ses_sender_email)
  
    domain_name = "EmailQueue"

    limit = self.limit

    # The current time in date string format
    date_format = "%Y-%m-%dT%H:%M:%S.000Z"
    current_time = time.gmtime()
    date_scheduled_before = time.strftime(date_format, current_time)

    # Connect to DB
    db_conn = self.db.connect()

    email_items = self.db.elife_get_email_queue_items(
      query_type = "items",
      limit = limit,
      date_scheduled_before = date_scheduled_before)
    
    for e in email_items:
      item_name = e.name
      item_attrs = {}
      try:
        result = self.send_email(
          sender_email    = e["sender_email"],
          recipient_email = e["recipient_email"],
          subject         = e["subject"],
          body            = e["body"],
          format          = e["format"])
      except KeyError:
        # Missing an expected value, handle exception and
        #  continue the loop
        continue
        
      if(result is True):
        item_attrs["date_sent_timestamp"] = calendar.timegm(time.gmtime())
        item_attrs["sent_status"] = True
        self.db.put_attributes(domain_name, item_name, item_attrs)
      elif(result is False):
        # Did not send correctly
        item_attrs["sent_status"] = False
        self.db.put_attributes(domain_name, item_name, item_attrs)
    return True
  
  def send_email(self, sender_email, recipient_email, subject, body, format = "text"):
    """
    Using Amazon SES service
    """
    
    ses_conn = boto.ses.connect_to_region(self.settings.simpledb_region, aws_access_key_id = self.settings.aws_access_key_id, aws_secret_access_key = self.settings.aws_secret_access_key)
    
    try:
      ses_conn.send_email(
        source       = sender_email,
        to_addresses = recipient_email,
        subject      = subject,
        body         = body,
        format       = format)
      return True
    except boto.ses.exceptions.SESAddressNotVerifiedError:
      # For now, try to ask the recipient to verify
      ses_conn.verify_email_address(recipient_email)
      return False
