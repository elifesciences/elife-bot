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

from ftplib import FTP
import ftplib

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
        
        # Bucket settings
        self.article_bucket = settings.bucket
        
        # Local directory settings
        self.TMP_DIR = "tmp_dir"
        self.FTP_TO_SOMEWHERE_DIR = "ftp_outbox"
        
        # Outgoing FTP settings are set later
        self.FTP_URI = None
        self.FTP_USERNAME = None
        self.FTP_PASSWORD = None
        self.FTP_CWD = None
        self.FTP_SUBDIR = []
        
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Data passed to this activity
        elife_id = data["data"]["elife_id"]
        workflow = data["data"]["workflow"]
        
        # Create output directories
        self.create_activity_directories()
        
        # Data provider
        self.db = dblib.SimpleDB(self.settings)
        # Connect to DB
        self.db_conn = self.db.connect()
        
        # Download the S3 objects
        self.download_files_from_s3(elife_id, workflow)
        
        # Set FTP settings
        self.set_ftp_settings(elife_id, workflow)
        
        # FTP to endpoint
        if workflow == 'HEFCE':
            file_type = "/*.zip"
            zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR + file_type)
            self.ftp_to_endpoint(zipfiles, self.FTP_SUBDIR)
        if workflow == 'Cengage':
            file_type = "/*.zip"
            zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR + file_type)
            self.ftp_to_endpoint(zipfiles)
         
        # Return the activity result, True or False
        result = True

        return result

    def set_ftp_settings(self, doi_id, workflow):
        """
        Set the outgoing FTP server settings based on the
        workflow type specified
        """
                    
        if workflow == 'HEFCE':
            self.FTP_URI = self.settings.HEFCE_FTP_URI
            self.FTP_USERNAME = self.settings.HEFCE_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.HEFCE_FTP_PASSWORD
            self.FTP_CWD =  self.settings.HEFCE_FTP_CWD
            # Subfolders to create when FTPing
            self.FTP_SUBDIR.append(str(doi_id).zfill(5))
            
        if workflow == 'Cengage':
            self.FTP_URI = self.settings.CENGAGE_FTP_URI
            self.FTP_USERNAME = self.settings.CENGAGE_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.CENGAGE_FTP_PASSWORD
            self.FTP_CWD =  self.settings.CENGAGE_FTP_CWD
        
    def download_files_from_s3(self, doi_id, workflow):
        
        if workflow == 'HEFCE':
            # Download files from the articles bucket
            self.download_data_file_from_s3(doi_id, 'xml', workflow)
            self.download_data_file_from_s3(doi_id, 'pdf', workflow)
            if int(doi_id) != 855:
                self.download_data_file_from_s3(doi_id, 'img', workflow)
            if int(doi_id) != 1311:
                self.download_data_file_from_s3(doi_id, 'suppl', workflow)
            self.download_data_file_from_s3(doi_id, 'video', workflow)
            self.download_data_file_from_s3(doi_id, 'jpg', workflow)
            self.download_data_file_from_s3(doi_id, 'figures', workflow)
            
        if workflow == 'Cengage':
            # Download files from the articles bucket
            self.download_data_file_from_s3(doi_id, 'xml', workflow)
            self.download_data_file_from_s3(doi_id, 'pdf', workflow)
        
    def download_data_file_from_s3(self, doi_id, file_data_type, workflow):
        """
        Find the file of type file_data_type from the simpleDB provider
        If it exists, download it
        """
        item_list = self.db.elife_get_article_S3_file_items(
            file_data_type = file_data_type,
            doi_id = str(doi_id).zfill(5),
            latest = True)

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.article_bucket)

        for item in item_list:
            # Download objects from S3 and save to disk
            s3_key_name = item['name']

            s3_key = bucket.get_key(s3_key_name)

            filename = s3_key_name.split("/")[-1]

            filename_plus_path = (self.get_tmp_dir() + os.sep +
                                  self.FTP_TO_SOMEWHERE_DIR + os.sep + filename)
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()
                    
        
    def ftp_upload(self, ftp, file):
        ext = os.path.splitext(file)[1]
        #print file
        uploadname = file.split(os.sep)[-1]
        if ext in (".txt", ".htm", ".html"):
            ftp.storlines("STOR " + file, open(file))
        else:
            #print "uploading " + uploadname
            ftp.storbinary("STOR " + uploadname, open(file, "rb"), 1024)
            #print "uploaded " + uploadname
    
    def ftp_cwd_mkd(self, ftp, sub_dir):
        """
        Given an FTP connection and a sub_dir name
        try to cwd to the directory. If the directory
        does not exist, create it, then cwd again
        """
        cwd_success = None
        try:
            ftp.cwd(sub_dir)
            cwd_success = True
        except ftplib.error_perm:
            # Directory probably does not exist, create it
            ftp.mkd(sub_dir)
            cwd_success = False
        if cwd_success is not True:
            ftp.cwd(sub_dir)
        
        return cwd_success
    
    def ftp_to_endpoint(self, uploadfiles, sub_dir_list = None):
        for uploadfile in uploadfiles:
            ftp = FTP(self.FTP_URI, self.FTP_USERNAME, self.FTP_PASSWORD)
            self.ftp_cwd_mkd(ftp, "/")
            if self.FTP_CWD != "":
                self.ftp_cwd_mkd(ftp, self.FTP_CWD)
            if sub_dir_list is not None:
                for sub_dir in sub_dir_list:
                    self.ftp_cwd_mkd(ftp, sub_dir)
            
            self.ftp_upload(ftp, uploadfile)
            ftp.quit()


    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.get_tmp_dir() + os.sep + self.TMP_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR)
        except:
            pass