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
        self.xml_bucket = settings.bot_bucket
        self.xml_folder = "jats/"
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
        
        # Get the volume number from the XML
        volume = self.get_volume_from_xml(elife_id)
        
        # Set FTP settings
        self.set_ftp_settings(elife_id, workflow, volume)
        
        # FTP to endpoint
        file_type = "/*.zip"
        zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR + file_type)
        self.ftp_to_endpoint(zipfiles, self.FTP_SUBDIR)
        
        # Add the go.xml file
        self.create_go_xml_file(
            "coll",
            self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR,
            self.get_volume_from_xml(elife_id)
            )
        file_type = "/*.xml"
        zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR + file_type)
        self.ftp_to_endpoint(zipfiles, self.FTP_SUBDIR)
        
        # Return the activity result, True or False
        result = True

        return result

    def set_ftp_settings(self, doi_id, workflow, volume):
        """
        Set the outgoing FTP server settings based on the
        workflow type specified
        """
        
        if workflow == 'HWX':
            self.FTP_URI = self.settings.HWX_FTP_URI
            self.FTP_USERNAME = self.settings.HWX_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.HWX_FTP_PASSWORD
            self.FTP_CWD =  self.settings.HWX_FTP_CWD
            # Subfolders to create when FTPing
            self.FTP_SUBDIR.append('volume' + str(volume))
            self.FTP_SUBDIR.append(str(doi_id).zfill(5))
        
    def download_files_from_s3(self, doi_id, workflow):
        
        if workflow == 'HWX':
            # Download XML
            self.download_jats_xml_from_s3(doi_id, workflow)
            # Downlaod other files
            self.download_data_file_from_s3(doi_id, 'pdf', workflow)
            self.download_data_file_from_s3(doi_id, 'img', workflow)
            self.download_data_file_from_s3(doi_id, 'suppl', workflow)
            self.download_data_file_from_s3(doi_id, 'video', workflow)
            
            # Create the inline-media zip file
            self.create_inline_media_zip(doi_id)

            
    def create_inline_media_zip(self, doi_id):
        """
        If there is a video and/or suppl file downloaded,
        then create a new inline-media.zip file and add
        the contents of them to the new file
        """
        
        file_types = ["/*.video.zip", "/*.suppl.zip"]
        zip_temp_dir = self.get_tmp_dir() + os.sep + self.TMP_DIR + os.sep + 'zip_tmp'
        output_dir = self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR
        
        # Create the zip temp directory if it does not exist
        try:
            os.mkdir(zip_temp_dir)
        except:
            pass
        
        # Move the files to the temp directory
        movefiles = []
        for file_type in file_types:
            dirfiles = (glob.glob(output_dir + file_type))
            movefiles = movefiles + dirfiles
            
        for mf in movefiles:
            file_name = zip_temp_dir + os.sep + mf.split(os.sep)[-1]
            shutil.move(mf, file_name)
        
        # Get a list of zip files providing the input
        inputfiles = []
        for file_type in file_types:
            dirfiles = (glob.glob(zip_temp_dir + file_type))
            inputfiles = inputfiles + dirfiles
        
        # Do not contine if there are no input files
        if len(inputfiles) <= 0:
            return
        
        # Create the inline-media zip file and open it
        inlinemedia_filename = 'elife' + str(doi_id).zfill(5) + '.inline-media.zip'
        inlinemedia_filename_plus_path = (output_dir
                                          + os.sep + inlinemedia_filename)
        inlinemedia_zipfile = zipfile.ZipFile(inlinemedia_filename_plus_path, 'w')
        
        # For each of the zip input files, extract the contents and
        #  add them to the inline-media zip file
        for zipfile_name in inputfiles:
            current_zipfile = zipfile.ZipFile(zipfile_name, 'r')
            
            filelist = current_zipfile.namelist()
            for filename in filelist:
                path = zip_temp_dir + os.sep
                filename_plus_path = path + filename
                
                current_zipfile.extract(filename, path)
                
                inlinemedia_zipfile.write(filename_plus_path, filename)
                
            current_zipfile.close()
            
        inlinemedia_zipfile.close()
        
    def download_jats_xml_from_s3(self, doi_id, workflow):
        """
        Download the JATS XML from S3, used temporarily
        as a source of XML during resupply process
        """
        jats_xml_s3_key_name = self.xml_folder + 'elife' + str(doi_id).zfill(5) + '.xml'
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.xml_bucket)
        
        s3_key = bucket.get_key(jats_xml_s3_key_name)

        filename = jats_xml_s3_key_name.split("/")[-1]

        filename_plus_path = self.get_tmp_dir() + os.sep + self.TMP_DIR + os.sep + filename
        mode = "wb"
        f = open(filename_plus_path, mode)
        s3_key.get_contents_to_file(f)
        f.close()
        
        # Zip it and save to ftp_outbox
        
        # Set the file name based on the workflow type
        file_data_type = 'xml'
        new_zipfile_name = self.get_filename_from_s3(doi_id, file_data_type)
        
        if workflow == 'HWX':
            # HWX workflow does not want the r1.xml.zip, r2.xml.zip style filename ending
            new_zipfile_name = self.get_hwx_zip_file_name(doi_id, file_data_type)
        
        new_zipfile_name_plus_path = (self.get_tmp_dir() + os.sep +
                                      self.FTP_TO_SOMEWHERE_DIR + os.sep +
                                      new_zipfile_name)
        
        new_zipfile = zipfile.ZipFile(new_zipfile_name_plus_path, 'w')
        new_zipfile.write(filename_plus_path, filename)
        new_zipfile.close()
        
    def get_hwx_zip_file_name(self, doi_id, file_data_type):
        """
        In supplying file names to HWX do not include the revision (r1, r2, etc.)
        portion, and base the name on the article volume
        """
        
        zipfile_name = None
        
        year = None
        volume = self.get_volume_from_xml(doi_id)
        if   volume == 1: year = 2012
        elif volume == 2: year = 2013
        elif volume == 3: year = 2014
        
        if year:
            zipfile_name = ('elife_' + str(year) + '_'
                            + str(doi_id).zfill(5) + '.'
                            + file_data_type + '.zip')
            
        return zipfile_name
        
    def get_filename_from_s3(self, doi_id, file_data_type):
        """
        In order to get the XML file revision file name,
        get the filename of the XML zip file from the bucket
        Expect to find only one result per request
        """
        filename = None
        
        item_list = self.db.elife_get_article_S3_file_items(
            file_data_type = file_data_type,
            doi_id = str(doi_id).zfill(5),
            latest = True)
        
        for item in item_list:
            # Download objects from S3 and save to disk
            s3_key_name = item['name']
            
            filename = s3_key_name.split("/")[-1]
        
        return filename
        
        
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
            if workflow == 'HWX' and filename.split(".")[-1] == 'zip':
                # HWX workflow does not want the r1.xml.zip, r2.xml.zip style filename ending
                filename = self.get_hwx_zip_file_name(doi_id, file_data_type)

            filename_plus_path = (self.get_tmp_dir() + os.sep +
                                  self.FTP_TO_SOMEWHERE_DIR + os.sep + filename)
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()
        
    def get_volume_from_xml(self, doi_id):
        """
        Temporary
        Instead of parsing the XML file we have some preset lists
        """
        volume_1_list = [3, 5, 7, 11, 13, 31, 47, 48, 49, 51, 65, 67, 68, 70, 78,
                         90, 93, 102, 109, 117, 171, 173, 181, 184, 205, 240, 242,
                         243, 248, 270, 281, 286, 301, 302, 311, 326, 340, 347,
                         351, 352, 353, 365, 385, 386, 387, 475]
        
        volume_2_list = [12, 36, 105, 116, 133, 160, 170, 178, 183, 190, 218, 220,
                         230, 231, 247, 260, 269, 278, 288, 290, 291, 299, 306, 308,
                         312, 321, 324, 327, 329, 333, 334, 336, 337, 348, 354, 358,
                         362, 367, 378, 380, 400, 411, 415, 421, 422, 425, 426, 429,
                         435, 444, 450, 452, 458, 459, 461, 467, 471, 473, 476, 477,
                         481, 482, 488, 491, 498, 499, 505, 508, 515, 518, 522, 523,
                         533, 534, 537, 542, 558, 563, 565, 569, 571, 572, 573, 577,
                         592, 593, 594, 603, 605, 615, 625, 626, 631, 632, 633, 638,
                         639, 640, 641, 642, 646, 647, 648, 654, 655, 658, 659, 663,
                         666, 668, 669, 672, 675, 676, 683, 691, 692, 699, 704, 708,
                         710, 712, 723, 726, 729, 731, 736, 744, 745, 747, 750, 757,
                         759, 762, 767, 768, 772, 776, 778, 780, 782, 785, 790, 791,
                         792, 799, 800, 801, 802, 804, 806, 808, 813, 822, 824, 825,
                         828, 842, 844, 845, 855, 856, 857, 861, 862, 863, 866, 868,
                         873, 882, 884, 886, 895, 899, 903, 905, 914, 924, 926, 932,
                         933, 940, 943, 947, 948, 951, 953, 954, 958, 960, 961, 963,
                         966, 967, 969, 971, 983, 992, 994, 996, 999, 1004, 1008, 1009,
                         1020, 1029, 1030, 1042, 1045, 1061, 1064, 1067, 1071, 1074,
                         1084, 1085, 1086, 1089, 1096, 1098, 1102, 1104, 1108, 1114,
                         1115, 1119, 1120, 1123, 1127, 1133, 1135, 1136, 1138, 1139,
                         1140, 1149, 1157, 1159, 1160, 1169, 1179, 1180, 1197, 1202,
                         1206, 1211, 1213, 1214, 1221, 1222, 1228, 1229, 1233, 1234,
                         1236, 1252, 1256, 1270, 1273, 1279, 1287, 1289, 1291, 1293,
                         1294, 1295, 1296, 1298, 1299, 1305, 1312, 1319, 1323, 1326,
                         1328, 1339, 1340, 1341, 1345, 1350, 1387, 1388, 1402, 1403,
                         1414, 1426, 1428, 1456, 1462, 1469, 1482, 1494, 1501, 1503,
                         1514, 1515, 1516, 1519, 1541, 1557, 1561, 1574, 1587, 1597,
                         1599, 1605, 1608, 1633, 1658, 1662, 1663, 1680, 1700, 1710,
                         1738, 1749, 1760, 1779, 1809, 1816, 1820, 1839, 1845, 1873,
                         1893, 1926, 1968, 1979, 2094]
        
        if int(doi_id) in volume_1_list:
            return 1
        elif int(doi_id) in volume_2_list:
            return 2
        else:
            return 3
        
    def create_go_xml_file(self, go_type, sub_dir, volume):
        """
        Create a go.xml file of the particular type and save it
        to the particular sub directory
        """
        go_xml_content = ""

        go_xml_content = self.get_go_xml_content(go_type, volume)

        # Write to disk
        go_xml_filename = sub_dir + os.sep + "go.xml"
        f = open(go_xml_filename, "w")
        f.write(go_xml_content)
        f.close()
        
    def get_go_xml_content(self, go_type, volume):
        """
        Given the type of go.xml file, return the content for it
        """
        go_xml_content = ('<?xml version="1.0"?>'
            '<!DOCTYPE HWExpress PUBLIC "-//HIGHWIRE//DTD HighWire Express Marker DTD v1.1.2HW//EN"'
            ' "marker.dtd">'
            '<HWExpress type="coll">'
            '<site>elife</site>'
            )
        go_xml_content += '<volume>' + str(volume) + '</volume>'
        go_xml_content += '</HWExpress>'
        
        return go_xml_content
        
        
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