import os
import boto.swf
import json
import random
import datetime
import importlib

import zipfile
import requests
import urlparse
import glob
import shutil

import activity

import boto.s3
from boto.s3.connection import S3Connection

"""
PublishPOA activity
"""

class activity_PublishPOA(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PublishPOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download POA files in outbox, zip, and publish."
        
        # Directory where POA library is stored
        self.poa_lib_dir_name = "elife-poa-xml-generation"
        
        # Where we specify the library to be imported
        self.elife_poa_lib = None
        
        # Import the libraries we will need
        self.import_imports()
        
        # Create output directories
        self.create_activity_directories()
        
        # Bucket for outgoing files
        self.publish_bucket = settings.bot_bucket
        self.outbox_folder = "poa/outbox/"
    
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Download the S3 objects
        # TODO!!!
        
        # Prepare for HW
        self.prepare_for_hw()
        
        # TODO!!! Publish files
        
        # TODO!  Assume all worked for now
        result = True

        return result

    def prepare_for_hw(self):
        """
        Using the POA prepare_xml_pdf_for_hw module
        """
        self.elife_poa_lib.prepare.prepare_pdf_xml_for_ftp()

    def import_imports(self):
        """
        Customised importing of the external library
        to override the settings
        MUST load settings module first, override the values
        BEFORE loading anything else, or the override will not take effect
        """
        
        # Load the files from parent directory - hellish imports but they
        #  seem to work now
        dir_name = self.poa_lib_dir_name
        
        self.import_poa_lib(dir_name)
        self.override_poa_settings(dir_name)
        self.import_poa_modules(dir_name)
    
    def import_poa_lib(self, dir_name):
        """
        POA lib import Step 1: import external library by directory name
        """
        self.elife_poa_lib = __import__(dir_name)
        
    def override_poa_settings(self, dir_name):
        """
        POA lib import Step 2: import settings modules then override
        """

        # Load external library settings
        importlib.import_module(dir_name + ".settings")
        
        settings = self.elife_poa_lib.settings
        
        # Override the settings
        settings.XLS_PATH                   = self.get_tmp_dir() + os.sep + 'ejp-csv' + os.sep
        settings.TARGET_OUTPUT_DIR          = self.get_tmp_dir() + os.sep + settings.TARGET_OUTPUT_DIR
        settings.STAGING_TO_HW_DIR          = self.get_tmp_dir() + os.sep + settings.STAGING_TO_HW_DIR
        settings.FTP_TO_HW_DIR              = self.get_tmp_dir() + os.sep + settings.FTP_TO_HW_DIR
        settings.MADE_FTP_READY             = self.get_tmp_dir() + os.sep + settings.MADE_FTP_READY
        settings.EJP_INPUT_DIR              = self.get_tmp_dir() + os.sep + settings.EJP_INPUT_DIR
        settings.STAGING_DECAPITATE_PDF_DIR = self.get_tmp_dir() + os.sep + settings.STAGING_DECAPITATE_PDF_DIR
        
    def import_poa_modules(self, dir_name = "elife-poa-xml-generation"):
        """
        POA lib import Step 3: import modules now that settings are overridden
        """

        # Now we can continue with imports
        self.elife_poa_lib.prepare = importlib.import_module(dir_name + ".prepare_xml_pdf_for_hw")
        
    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.elife_poa_lib.settings.XLS_PATH)
        except:
            pass
        
        try:
            os.mkdir(self.elife_poa_lib.settings.TARGET_OUTPUT_DIR)
            os.mkdir(self.elife_poa_lib.settings.STAGING_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.FTP_TO_HW_DIR)
            os.mkdir(self.elife_poa_lib.settings.MADE_FTP_READY)
            os.mkdir(self.elife_poa_lib.settings.EJP_INPUT_DIR)
            os.mkdir(self.elife_poa_lib.settings.STAGING_DECAPITATE_PDF_DIR)
        except:
            pass