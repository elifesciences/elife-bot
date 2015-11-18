import boto.swf
import json
import random
import datetime
import calendar
import time
import os
import zipfile
import shutil

import activity

import boto.s3
from boto.s3.connection import S3Connection

"""
UnzipLensJPG activity
"""

class activity_UnzipLensJPG(activity.activity):
  
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)
    
        self.name = "UnzipLensJPG"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*5
        self.description = "Download a S3 object for lens jpg files, unzip and save to the elife-cdn bucket."
        
        # Local directory settings
        self.TMP_DIR = self.get_tmp_dir() + os.sep + "tmp_dir"
        self.INPUT_DIR = self.get_tmp_dir() + os.sep + "input_dir"
        self.OUTPUT_DIR = self.get_tmp_dir() + os.sep + "output_dir"
        
        self.elife_id = None
        self.document = None
        
        self.jpg_subfolder = 'jpg'
        
        self.input_bucket = settings.lens_jpg_bucket
        self.output_bucket = self.settings.cdn_bucket        

    def do_activity(self, data = None):
        """
        Do the work
        """
        if(self.logger):
          self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        self.elife_id = self.get_elife_id_from_data(data)
        
        # Download the S3 object
        self.document = self.get_document_from_data(data)
        
        # Create output directories
        self.create_activity_directories()
        
        # Download the S3 objects
        self.download_files_from_s3(self.document)
        
        filename = self.INPUT_DIR + os.sep + self.document
        # Unzip article file
        self.unzip_or_move_file(filename, self.TMP_DIR)
        
        self.move_approved_files()
        
        self.upload_jpg()

        if(self.logger):
          self.logger.info('UnzipLensJPG: %s' % self.elife_id)
    
        return True
    
    def get_elife_id_from_data(self, data):
        self.elife_id = data["data"]["elife_id"]
        return self.elife_id
  
    def get_document_from_data(self, data):
        self.document = data["data"]["document"]
        return self.document
  
    def move_approved_files(self):
        """ Move files from tmp dir to the output dir """
        to_dir = self.OUTPUT_DIR
        for file_name in self.file_list(self.TMP_DIR):
            new_file_name = self.file_name_from_name(file_name)
            shutil.copyfile(file_name, to_dir + os.sep + new_file_name)
  
    def cdn_base_prefix(self, elife_id):
        return 'elife-articles/' + str(elife_id).zfill(5) + '/'
    
    def upload_jpg(self):
        """
        Upload JPG to CDN
        """
        file_list = []
        for file_name in self.file_list(self.OUTPUT_DIR):
            if self.file_extension(file_name) == 'jpg':
                file_list.append(file_name)
        prefix = self.cdn_base_prefix(self.elife_id) + self.jpg_subfolder + '/'
        self.upload_files_to_cdn(prefix, file_list)
    
    def upload_files_to_cdn(self, prefix, file_list, content_type = None):
        """
        Actually upload to S3 CDN bucket
        """
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.output_bucket)
        
        for file_name in file_list:
            s3_key_name = prefix + self.file_name_from_name(file_name)
            s3_key = boto.s3.key.Key(bucket)
            s3_key.key = s3_key_name
            s3_key.set_contents_from_filename(file_name, replace=True)
            if content_type:
                s3_key.set_metadata('Content-Type', content_type)

    def download_files_from_s3(self, document):
        
        if(self.logger):
            self.logger.info('downloading file ' + document)
  
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.input_bucket)
  
        s3_key_name = document
        s3_key = bucket.get_key(s3_key_name)

        filename = s3_key_name.split("/")[-1]

        filename_plus_path = (self.INPUT_DIR
                              + os.sep + filename)
        mode = "wb"
        f = open(filename_plus_path, mode)
        s3_key.get_contents_to_file(f)
        f.close()
  
    def unzip_or_move_file(self, file_name, to_dir, do_unzip = True):
        """
        If file extension is zip, then unzip contents
        If file the extension 
        """
        if (self.file_extension(file_name) == 'zip'
            and do_unzip is True):
            # Unzip
            if(self.logger):
                self.logger.info("going to unzip " + file_name + " to " + to_dir)
            myzip = zipfile.ZipFile(file_name, 'r')
            myzip.extractall(to_dir)
    
        elif self.file_extension(file_name):
            # Copy
            if(self.logger):
                self.logger.info("going to move and not unzip " + file_name + " to " + to_dir)
            shutil.copyfile(file_name, to_dir + os.sep + self.file_name_from_name(file_name))  

    def list_dir(self, dir_name):
        dir_list = os.listdir(dir_name)
        dir_list = map(lambda item: dir_name + os.sep + item, dir_list)
        return dir_list
    
    def folder_list(self, dir_name):
        dir_list = self.list_dir(dir_name)
        return filter(lambda item: os.path.isdir(item), dir_list)
    
    def file_list(self, dir_name):
        dir_list = self.list_dir(dir_name)
        return filter(lambda item: os.path.isfile(item), dir_list)

    def folder_name_from_name(self, input_dir, file_name):
        folder_name = file_name.split(input_dir)[1]
        folder_name = folder_name.split(os.sep)[1]
        return folder_name
    
    def file_name_from_name(self, file_name):
        name = file_name.split(os.sep)[-1]
        return name
    
    def file_extension(self, file_name):
        name = self.file_name_from_name(file_name)
        if name:
            if len(name.split('.')) > 1:
                return name.split('.')[-1]
            else:
                return None
        return None
       
    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.TMP_DIR)
            os.mkdir(self.INPUT_DIR)
            os.mkdir(self.OUTPUT_DIR)
            
        except:
            pass