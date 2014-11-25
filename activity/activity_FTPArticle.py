import os
import boto.swf
import json
import random
import datetime
import importlib
import calendar
import time

import zipfile
import requests
import urlparse
import glob
import shutil
import re

import activity

import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib

"""
FTPArticle activity
"""

class activity_FTPArticle(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "FTPArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download VOR files and publish by FTP to some particular place."
        
        # Track the success of some steps
        self.activity_status = None
        self.prepare_status = None
        self.approve_status = None
        self.ftp_status = None
        self.go_status = None
        self.outbox_status = None
        self.publish_status = None
        
        self.outbox_s3_key_names = None
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Return the activity result, True or False
        result = True

        return result
