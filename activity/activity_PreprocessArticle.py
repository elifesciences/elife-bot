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

import provider.s3lib as s3lib
import provider.simpleDB as dblib

from elifetools import parseJATS as parser
from elifetools import xmlio

from wand.image import Image

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import csv

from keyword_replacements import keywords

"""
PreprocessArticle activity
"""

class activity_PreprocessArticle(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PreprocessArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60*30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60*15
        self.description = "Download article zip files, rename or change them, and then upload them to a different bucket."
        
        # Bucket settings
        self.article_bucket = settings.bucket
        self.poa_bucket = settings.poa_packaging_bucket
        self.ppp_input_bucket = "elife-eps-renamed"
        
        # Bucket settings
        self.article_bucket = settings.bucket
        
        # Local directory settings
        self.TMP_DIR = self.get_tmp_dir() + os.sep + "tmp_dir"
        self.INPUT_DIR = self.get_tmp_dir() + os.sep + "input_dir"
        self.JUNK_DIR = self.get_tmp_dir() + os.sep + "junk_dir"
        self.ZIP_DIR = self.get_tmp_dir() + os.sep + "zip_dir"
        self.EPS_DIR = self.get_tmp_dir() + os.sep + "eps_dir"
        self.TIF_DIR = self.get_tmp_dir() + os.sep + "tif_dir" 
        self.OUTPUT_DIR = self.get_tmp_dir() + os.sep + "output_dir"
       
        # Bucket settings
        self.output_bucket = settings.publishing_buckets_prefix + settings.production_bucket
        # Temporarily upload to a folder during development
        self.output_bucket_folder = ""
        
        # Temporary detail of files from the zip files to an append log
        self.zip_file_contents_log_name = "rezip_article_zip_file_contents.txt"
        
        # journal
        self.journal = 'elife'
            
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        documents = []
        # Data passed to this activity
        if data and "data" in data and "document" in data["data"]:
            document = data["data"]["document"]
            documents.append(document)
        else:
            # Get document names from the buckets
            document = None
            documents = self.documents_in_first_bucket_not_the_second(self.ppp_input_bucket,
                                                                      self.output_bucket)
            if(self.logger):
                self.logger.info('PreprocessArticle found new zip files: %s' %
                                 json.dumps(documents, sort_keys=True, indent=4))


        # Create output directories
        self.create_activity_directories()

        if len(documents) <= 0:
            if(self.logger):
                self.logger.info('PreprocessArticle has no documents to process: ')
            verified = True

        for zip_doc in sorted(documents):
            article_documents = [zip_doc]

            # Download the S3 objects
            self.download_files_from_s3(article_documents)
            
            # Set the folder name in order to continue
            folder = self.INPUT_DIR + os.sep + ''.join(zip_doc.split('.')[0:-1])

            try:
                elife_id = int(folder.split('-')[1])
            except:
                elife_id = None             
            
            self.unzip_article_files(self.file_list(folder))
            self.rezip_article_folders()
            
            (fid, status, version) = self.profile_article(self.INPUT_DIR, folder)
            
            version = None
            # Rename the files
            file_name_map = self.rename_files(self.journal, fid, status,
                                              version, self.article_xml_file())
            
            (verified, renamed_list, not_renamed_list) = self.verify_rename_files(file_name_map)
            if(self.logger):
                self.logger.info("verified " + folder + ": " + str(verified))
                self.logger.info(file_name_map)

            if len(not_renamed_list) > 0:
                if(self.logger):
                    self.logger.info("not renamed " + str(not_renamed_list))
        
            # Convert the XML
            self.convert_xml(doi_id = elife_id,
                             xml_file = self.article_xml_file(),
                             file_name_map = file_name_map)
        
            # Get the new zip file name
            zip_file_name = folder.split(os.sep)[-1] + '.zip'
            self.create_new_zip(zip_file_name)
            
            if verified and zip_file_name:
                self.upload_article_zip_to_s3()
            
            # Partial clean up
            self.clean_directories(full = True)
            
        # Get a list of file names and sizes
        self.log_zip_file_contents()
        
        
        # Return the activity result, True or False
        if verified is True:
            result = True
        else:
            result = False

        return result

    def log_zip_file_contents(self):
        """
        For now, append zip file contents to a separate file
        """
        file_log = open(self.get_tmp_dir() + os.sep
                        + ".." + os.sep
                        + self.zip_file_contents_log_name, 'ab')
        for filename in self.file_list(self.ZIP_DIR):
            
            myzip = zipfile.ZipFile(filename, 'r')
            for i in myzip.infolist():
                file_log.write("\n" + filename.split(os.sep)[-1]
                               + "\t" + str(i.filename)
                               + "\t" + str(i.file_size))

    def documents_in_first_bucket_not_the_second(self, first_bucket_name, second_bucket_name):
        """
        Comparing the keys from one bucket to the other
        in order to get a list of keys to prcoess
        """
        s3_key_names = []
        
        file_extensions = ['.zip']
        # get item list from S3
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(first_bucket_name)
        first_bucket_s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket = bucket, file_extensions = file_extensions)
        
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(second_bucket_name)
        second_bucket_s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket = bucket)
        
        for first in first_bucket_s3_key_names:
            if first not in second_bucket_s3_key_names:
                s3_key_names.append(first)

        return s3_key_names

    def download_files_from_s3(self, documents):
        
        # VoR file download
        for document in documents:
            self.download_vor_files_from_s3(document)
        



    def get_poa_date_str_for_version(self, doi_id, version):
        """ """
        return self.get_date_str_for_version_from_csv('poa', doi_id, version)

    def get_vor_date_str_for_version(self, doi_id, version):
        """ """
        return self.get_date_str_for_version_from_csv('vor', doi_id, 1)
    
    def get_date_str_for_version_from_csv(self, status, doi_id, version):
        """
        Read the csv file for updated dates, and format as a date string value we want
        """
        date_str = None
        
        doi_col = 0
        date_col = 1
        status_col = 2
        version_col = 3
        
        doi = '10.7554/eLife.' + str(doi_id).zfill(5)
        
        csv_file_path = self.get_tmp_dir() + os.sep + self.article_dates_csv
        csvreader = csv.reader(open(csv_file_path, 'rb'), delimiter=',', quotechar='"')
        matched_rows = []
        for row in csvreader:
            try:
                if row[doi_col] == doi and row[status_col].lower() == status.lower():
                    matched_rows.append(row)
            except IndexError:
                if(self.logger):
                    self.logger.info('csv date file read error on column index')

        # Note: expect the csv to be sorted by date already
        
        row = None
        try:
            row = matched_rows[int(version)-1]
        except IndexError:
            if(self.logger):
                self.logger.info('csv matched rows could not find ' + status
                                 + ' version ' + str(int(version)-1) + ' of doi ' + str(doi))
        
        if row:
            date_struct = time.strptime(row[date_col], '%Y-%m-%d %H:%M:%S')
            date_str = time.strftime("%Y%m%d", date_struct)
            # Add midnight minutes to the end
            date_str += '000000'

        return date_str


    def download_vor_files_from_s3(self, document):
        """

        """
        if(self.logger):
            self.logger.info('downloading VoR file  ' + str(document))
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(self.ppp_input_bucket)
        
        s3_key_names = [document]

        subfolder_name = ''.join(document.split('.')[0:-1])

        self.download_s3_key_names_to_subfolder(bucket, s3_key_names, subfolder_name)
        
    def latest_revision_zip_key_name(self, s3_key_names, doi_id, status = 'vor'):
        """
        Given a list of s3 bucket object names (with no subfolder)
        a doi_id and a status of 'vor' or 'poa',
        Then find the zip file for the most recent revision
        """
        zip_s3_key_name = None
        
        # Find the latest revision zip file for this article
        name_prefix = 'elife-' + str(doi_id).zfill(5) + '-' + status + '-r'
        max_revision = None
        
        for key_name in s3_key_names:

            if name_prefix in key_name:
                # Look for the max revision number of all zip files for this article
                revision = None
                
                try:
                    part = key_name.replace(name_prefix, '')
                    revision = int(part.split('.')[0])
                except:
                    pass
                if ( (revision and not max_revision) or
                     (revision and max_revision and revision > max_revision)):
                    max_revision = revision
        
        if max_revision:
            zip_s3_key_name = name_prefix + str(max_revision) + '.zip'
                
        return zip_s3_key_name
        
    def download_s3_key_names_to_subfolder(self, bucket, s3_key_names, subfolder_name):
        
        for s3_key_name in s3_key_names:
            # Download objects from S3 and save to disk
            
            s3_key = bucket.get_key(s3_key_name)

            filename = s3_key_name.split("/")[-1]

            # Make the subfolder if it does not exist yet
            try:
                os.mkdir(self.INPUT_DIR + os.sep + subfolder_name)
            except:
                pass

            filename_plus_path = (self.INPUT_DIR
                                  + os.sep + subfolder_name
                                  + os.sep + filename)
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()

    def upload_article_zip_to_s3(self):
        """
        Upload the article zip files to S3
        """
        
        bucket_name = self.output_bucket
        bucket_folder_name = self.output_bucket_folder
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
    
        for file in self.file_list(self.ZIP_DIR):
            s3_key_name = bucket_folder_name + file.split(os.sep)[-1]
            s3key = boto.s3.key.Key(bucket)
            s3key.key = s3_key_name
            s3key.set_contents_from_filename(file, replace=True)
            if(self.logger):
                self.logger.info("uploaded " + s3_key_name + " to s3 bucket " + bucket_name)


    
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
    
    def file_type(self, file_name):
        """
        File type is the file extension is not a zip, and
        if a zip, then look for the second or last or third to last element
        that is not r1, r2, etc.
        """
        if not self.file_extension(file_name):
            return None
        
        if self.file_extension(file_name) != 'zip':
            return self.file_extension(file_name)
        else:
            if not file_name.split('.')[-2].startswith('r'):
                return file_name.split('.')[-2]
            elif not file_name.split('.')[-3].startswith('r'):
                return file_name.split('.')[-3]
        return None
    
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
            
        # Clean up after unzipping a PoA supp.zip file by moving the manifest.xml file
        if (self.file_extension(file_name) == 'zip'
            and self.is_poa_ds_file(file_name) is True
            and do_unzip is True):
            if(self.logger):
                self.logger.info("moving PoA zip manifest.xml to the junk folder")
            shutil.move(to_dir + os.sep + 'manifest.xml', self.JUNK_DIR + os.sep + 'manifest.xml')
    
    
    def is_poa_ds_file(self, file_name):
        if self.file_name_from_name(file_name).split('.')[0].endswith('_ds'):
            return True
        return False
    
    def approve_file(self, file_name):
        """
        Choose which files to unzip and keep, basically do not need svg or jpg packages
        """
        good_zip_file_types = ['xml','pdf','img','video','suppl','figures']
        if self.file_type(file_name) in good_zip_file_types:
            return True
        # Check for PoA DS files
        if self.is_poa_ds_file(file_name):
            return True
        # Check for new style PPP zip files
        if '-vor-' in file_name:
            return True
        
        # Default
        return False
    
    
    def unzip_article_files(self, file_list):
        
        for file_name in file_list:
            self.unzip_or_move_file(file_name, self.TMP_DIR)


    def rezip_article_folders(self):
        
        # Check for any folders in TMP_DIR, and zip them if found
        #  these are likely to be .zip files in the article XML but were
        #  not supplied to S3 as a zip within a zip
        for folder_name in self.folder_list(self.TMP_DIR):
            if(self.logger):
                self.logger.info("found a folder in the tmp_dir to be rezipped " + folder_name)
            
            folder_name_only = folder_name.split(os.sep)[-1]
            zip_file_name = folder_name_only + '.zip'
            new_zipfile = zipfile.ZipFile(self.TMP_DIR + os.sep + zip_file_name,
                                          'w', zipfile.ZIP_DEFLATED, allowZip64 = True)
            
            # Read all files in all subfolders and add them to the new zip file
            for root, dirs, files in os.walk(folder_name):
                for name in files:
                    # df = path to the file on disk
                    df = os.path.join(root, name)
                    # filename = folder + file name we want in the zip file
                    filename = df.split(folder_name)[-1]
                    
                    if(self.logger):
                        self.logger.info("df: " + df)
                        self.logger.info("filename: " + filename)
                        
                    new_zipfile.write(df, filename)
            new_zipfile.close()
    
    def add_filename_fid(self, filename, fid):
        return filename + '-' + str(fid).zfill(5)
        
    def add_filename_status(self, filename, status):
        return filename + '-' + status.lower()
        
    def add_filename_version(self, filename, version):
        if version is None:
            return filename
        else:
            return filename + '-' + 'v' + str(version)
            
    def add_filename_asset(self, filename, asset, ordinal = None):
        filename += '-' + asset
        if ordinal and asset not in ['dec', 'resp']:
            filename += str(ordinal)
        return filename
    
    def new_filename(self, soup, old_filename, journal, fid, status, version = None):
        
        new_filename = None
        
        new_filename = self.new_filename_special(soup, old_filename, journal, fid, status, version)
        if not new_filename:
            new_filename = self.new_filename_generic(soup, old_filename, journal, fid, status, version)  
            
        return new_filename
    
    def new_filename_special(self, soup, old_filename, journal, fid, status, version):
        """
        Special files to be renamed in a certain way, if it matches any of these rules
        If it does not, then try new_filename_generic on the file name
        """
        new_filename = None
    
        if old_filename.endswith('.xml'):
            # Confirm it is the article XML file
            if (old_filename == 'elife' + str(fid).zfill(5) + '.xml'
                or old_filename.startswith('elife_poa_e' + str(fid).zfill(5))
                or old_filename == 'elife-' + str(fid).zfill(5) + '.xml'):
                new_filename = journal
                new_filename = self.add_filename_fid(new_filename, fid)
                new_filename = self.add_filename_version(new_filename, version)
                new_filename += '.xml'
            
        if old_filename.endswith('.pdf'):
            # Confirm it is the article PDF file or figures PDF
            if (old_filename == 'elife' + str(fid).zfill(5) + '.pdf'
                or old_filename.startswith('decap_elife_poa_e' + str(fid).zfill(5))
                or old_filename == 'elife' + str(fid).zfill(5) + '-figures.pdf'
                or old_filename == 'elife-' + str(fid).zfill(5) + '-figures.pdf'):
                new_filename = journal
                new_filename = self.add_filename_fid(new_filename, fid)
                if 'figures' in old_filename:
                    new_filename += '-figures'
                new_filename = self.add_filename_version(new_filename, version)
                new_filename += '.pdf'
                
        if old_filename.endswith('_ds.zip') or old_filename.endswith('_Supplemental_files.zip'):
            # PoA digital supplement file
            # TODO - may want to unwrap the zip and rename its child zip
            new_filename = journal
            new_filename = self.add_filename_fid(new_filename, fid)
            new_filename += '-supp'
            new_filename = self.add_filename_version(new_filename, version)
            new_filename += '.zip'
            
        # Special case for 04493 files
        if int(fid) == 4493 and old_filename.endswith('.zip') and new_filename is None:
            # A PoA 04493 video file, that is not a supp.zip file use it as is
            new_filename = old_filename
    
        return new_filename
    
    def parent_levels_by_type(self, item):
        """
        Given an item dict representing a matched tag,
        depending on its type, it will have different parent levels
        """
        # Here we want to set the parentage differently for videos
        #  because those items are their own parents, in a way
        if ('type' in item and item['type'] == 'media'
            and 'mimetype' in item and item['mimetype'] == 'video'):
            first_parent_level = ''
            second_parent_level = 'parent_'
            third_parent_level = 'p_parent_'
        else:
            first_parent_level = 'parent_'
            second_parent_level = 'p_parent_'
            third_parent_level = 'p_p_parent_'
        
        return first_parent_level, second_parent_level, third_parent_level
    
    def new_filename_generic(self, soup, old_filename, journal, fid, status, version):
        """
        After filtering out known exceptions for file name renaming,
        this will try and get a new file name based on the old filename
        """
        new_filename = None
        
            
        
        # File extension
        extension = self.file_extension(old_filename)
        if extension is None:
            return None
        new_extension = '.' + extension.lower()
    
        (asset, type, ordinal, parent_type, parent_ordinal,
        p_parent_type, p_parent_ordinal) = self.asset_details(fid, old_filename, soup)
    
        # For now, only allow ones that have an ordinal,
        #  to be sure we matched the full start of the file name
        if not ordinal:
            if(self.logger):
                self.logger.info('found no ordinal for ' + old_filename)
            return None
        
        if not asset:
            if(self.logger):
                self.logger.info('found no asset for ' + old_filename)
        
        new_filename = journal
        new_filename = self.add_filename_fid(new_filename, fid)
        
        # Need to lookup the item again to get the parent levels
        item = self.scan_soup_for_xlink_href(old_filename, soup)
        (first_parent_level, second_parent_level, third_parent_level) = \
            self.parent_levels_by_type(item)
        
        if p_parent_type:
            # TODO - refactor to get the asset name
            p_parent_asset = self.asset_from_soup(old_filename, soup, third_parent_level)
            if not p_parent_asset:
                if(self.logger):
                    self.logger.info('found no p_parent_asset for ' + old_filename)
            else:
                new_filename = self.add_filename_asset(new_filename, p_parent_asset, p_parent_ordinal)
        
        if parent_type:
            # TODO - refactor to get the asset name
            parent_asset = self.asset_from_soup(old_filename, soup, second_parent_level)
            if not parent_asset:
                if(self.logger):
                    self.logger.info('found no parent_asset for ' + old_filename)
            else:
                new_filename = self.add_filename_asset(new_filename, parent_asset, parent_ordinal)

        if asset:
            new_filename = self.add_filename_asset(new_filename, asset, ordinal)
        
        # Add version number
        if asset and asset == 'media':
            # Media video files, do not add version number
            pass
        else:
            new_filename = self.add_filename_version(new_filename, version)
        
        # Add file extension
        new_filename += new_extension
    
        return new_filename
    
    def asset_details(self, fid, old_filename, soup):
        
        asset = None
        type = None
        ordinal = None
        parent_type = None
        parent_ordinal = None
        p_parent_type = None
        p_parent_ordinal = None
        
        item = self.scan_soup_for_xlink_href(old_filename, soup)
        if item:
            type = item.get('type')
            
        # Here we want to set the parentage differently for videos
        #  because those items are their own parents, in a way
        first_parent_level = None
        second_parent_level = None
        third_parent_level = None
        if item:
            (first_parent_level, second_parent_level, third_parent_level) = \
                self.parent_levels_by_type(item)
        
        asset = self.asset_from_soup(old_filename, soup, first_parent_level)
        
        # Get parent details
        details = self.parent_details_from_soup(old_filename, soup, first_parent_level)
        if details:
            type = details['type']
            if 'sibling_ordinal' in details:
                ordinal = details['sibling_ordinal']
        if not ordinal:
            # No parent, use the actual element ordinal
            details = self.details_from_soup(old_filename, soup)
            if details:
                ordinal = details['ordinal']
            
        details = self.parent_details_from_soup(old_filename, soup, second_parent_level)
        if details:
            parent_type = details['type']
            parent_ordinal = details['sibling_ordinal']
            
        details = self.parent_details_from_soup(old_filename, soup, third_parent_level)
        if details:
            p_parent_type = details['type']
            p_parent_ordinal = details['sibling_ordinal']
        
        return asset, type, ordinal, parent_type, parent_ordinal, p_parent_type, p_parent_ordinal
    
    def items_to_match(self, soup):
        graphics = parser.graphics(soup)
        media = parser.media(soup)
        self_uri = parser.self_uri(soup)
        inline_graphics = parser.inline_graphics(soup)
        return graphics + media + self_uri + inline_graphics
    
    def scan_soup_for_xlink_href(self, xlink_href, soup):
        """
        Look for the usual suspects that have an xlink_href of interest
        and try to match it
        """
    
        for item in self.items_to_match(soup):
            if 'xlink_href' in item:
                # Try and match the exact filename first
                if item['xlink_href'] == xlink_href:
                    return item
                elif item['xlink_href'] == xlink_href.split('.')[0]:
                    # Try and match without the file extension
                    return item
        return None
    
    def asset_from_soup(self, old_filename, soup, level):
        asset = None
        item = self.scan_soup_for_xlink_href(old_filename, soup)
        
        if item:
            if level + 'type' in item:
                # Check for a parent_type
                if item[level + 'type'] == 'fig':
                    if level + 'asset' in item and item[level + 'asset'] == 'figsupp':
                        asset = 'figsupp'
                    else:
                        asset = 'fig'
                elif level + 'asset' in item:
                    # If asset is set, use it
                    asset = item[level + 'asset']
                elif item[level + 'type'] == 'supplementary-material':
                    asset = 'supp'
                # TODO may want a different subarticle value
                elif item[level + 'type'] == 'sub-article':
                    asset = 'subarticle'
                elif 'mimetype' in item and item['mimetype'] == 'video':
                    asset = 'media'
            elif 'mimetype' in item and item['mimetype'] == 'video':
                asset = 'media'
            elif 'inf' in old_filename:
                asset = 'inf'
                
        return asset
        
    
    def details_from_soup(self, old_filename, soup):
        details = {}
    
        matched_item = self.scan_soup_for_xlink_href(old_filename, soup)
        if not matched_item:
            return None
    
        if 'ordinal' in matched_item:
            details['ordinal'] = matched_item['ordinal']
    
        return details
    
    def parent_details_from_soup(self, old_filename, soup, level):
        if level not in ['', 'parent_', 'p_parent_', 'p_p_parent_']:
            return None
        
        details = {}
        matched_item = self.scan_soup_for_xlink_href(old_filename, soup)
        if not matched_item:
            return None
        
        if level + 'type' in matched_item:
            details['type'] = matched_item[level + 'type']
        if level + 'mimetype' in matched_item:
            details['mimetype'] = matched_item[level + 'mimetype']
        if level + 'sibling_ordinal' in matched_item:
            if level + 'asset' in matched_item and matched_item[level + 'asset'] == 'figsupp':
                # Subtract 1 from ordinal for figure supplements for now
                #  so the first figure is ignored from the count
                details['sibling_ordinal'] = matched_item[level + 'sibling_ordinal'] - 1
            else:
                details['sibling_ordinal'] = matched_item[level + 'sibling_ordinal']
    
        if len(details) > 0:
            return details
        else:
            return None
    
    
    def rename_files(self, journal, fid, status, version, xml_file):
        
        file_name_map = {}
        
        # Ignore these files we do not want them anymore
        ignore_files = ['elife05087s001.docx', 'elife05087s002.docx',
                        'elife08501f005.tif', 'elife09248fs002.tif',
                        'elife03275t001.tif', 'elife03275t002.tif',
                        'elife03275t003.tif', 'elife03275t004.tif',
                        'elife03275t005.tif', 'elife03275t006.tif',
                        'elife-10721-code1.zip']
                    
        # Get a list of all files
        dirfiles = self.file_list(self.TMP_DIR)
        
        soup = self.article_soup(xml_file)
        
        for df in dirfiles:
            filename = df.split(os.sep)[-1]
            
            if filename in ignore_files:
                continue
            
            # Get the new file name
            file_name_map[filename] = None
            renamed_filename = self.new_filename(soup, filename, journal, fid, status, version)
            
            if renamed_filename:
                file_name_map[filename] = renamed_filename
            else:
                if(self.logger):
                    self.logger.info('there is no renamed file for ' + filename)
        
        for old_name,new_name in file_name_map.iteritems():
            if new_name is not None:
                shutil.move(self.TMP_DIR + os.sep + old_name, self.OUTPUT_DIR + os.sep + new_name)
        
        return file_name_map
    
    def verify_rename_files(self, file_name_map):
        """
        Each file name as key should have a non None value as its value
        otherwise the file did not get renamed to something new and the
        rename file process was not complete
        """
        verified = True
        renamed_list = []
        not_renamed_list = []
        for k,v in file_name_map.items():
            if v is None:
                verified = False
                not_renamed_list.append(k)
            else:
                renamed_list.append(k)
                
        return (verified, renamed_list, not_renamed_list)
    
    def convert_xml(self, doi_id, xml_file, file_name_map):

        # Register namespaces
        xmlio.register_xmlns()
        
        root = xmlio.parse(xml_file)
        
        # Convert xlink href values
        total = xmlio.convert_xlink_href(root, file_name_map)
        # TODO - compare whether all file names were converted
        
        # Set graphic file extensions
        root = self.add_graphic_file_extensions_in_xml(doi_id, root)
        
        # Update or change JATS dtd-schema version
        self.dtd_version_to_xml(root)
        
        # Capitalise subject group values in article categories
        root = self.subject_group_convert_in_xml(root)
        
        # Convert research organism kwd tags
        root = self.research_organism_kwd_convert_in_xml(root, doi_id)
        
        # Wrap citation collab tags in person-group if they are not already
        root = self.element_citation_collab_wrap_in_xml(root)
        
        # Remove university from institution tags
        root = self.institution_university_convert_in_xml(root)

        # Fix sub-article titles
        root = self.sub_article_title_convert_in_xml(root)
        
        soup = self.article_soup(self.article_xml_file())
        
        # VoR files
        if not parser.is_poa(soup):

            # Rename video media file id attributes
            root = self.change_media_video_id_in_xml(doi_id, root)

        # Author keywords replacements
        root = self.author_keyword_replacements_in_xml(doi_id, root)

        # Change &#8211; en-rule to hyphen
        root = self.author_keyword_en_rule_in_xml(doi_id, root)

        # Start the file output
        reparsed_string = xmlio.output(root)

        # Remove extra whitespace here for PoA articles to clean up and one VoR file too
        reparsed_string = reparsed_string.replace("\n",'').replace("\t",'')
        
        f = open(xml_file, 'wb')
        f.write(reparsed_string)
        f.close()
    
    def dtd_version_to_xml(self, root):
        root.set('dtd-version', '1.1d3')

    def change_author_notes_xml_00731(self, root):
        """
        Single article edit
        """
        for p_tag in root.findall('.//author-notes/fn[@id="fn1"]/p'):
            p_tag.text = "Sophien Kamoun, Johannes Krause, Marco Thines, and Detlef Weigel are listed in alphabetical order"

        return root
    
    def change_kwd_group_xml_00051(self, root):
        """
        Single article edit
        """
        for kwd_group_tag in root.findall('.//kwd-group'):
            if kwd_group_tag.get('kwd-group-type') is None:
                # No group type, this one should be author keywords
                kwd_group_tag.set('kwd-group-type', 'author-keywords')

        return root
    
    def change_editor_aff_xml_03125(self, root):
        """
        Single article edit
        """
        for aff_tag in root.findall('.//contrib[@contrib-type="editor"]/aff'):
            for institution_tag in aff_tag.findall('.//institution'):
                if institution_tag.text.strip() == '':
                    institution_tag.text = 'Max Planck Institute for Marine Microbiology'
            for country_tag in aff_tag.findall('.//country'):
                if country_tag.text.strip() == '':
                    country_tag.text = 'Germany' 

        return root
    
    def add_graphic_file_extensions_in_xml(self, doi_id, root):
        """
        
        """
        tags = ['.//graphic', './/inline-graphic']
        for tag_name in tags:
            for tag in root.findall(tag_name):
                href = tag.get('{http://www.w3.org/1999/xlink}href')
                if href and len(href.split('.')) <= 1:
                    
                    # Default extension
                    extension = '.tif'
                    # extension = ''
                    
                    if int(doi_id) == 2020 or int(doi_id) == 3318:
                        # 02020
                        gifs_02020 = ["elife02020f002"]
                        
                        # 03318
                        gifs_03318 = ["elife03318f005", "elife03318f006",
                                        "elife03318f007", "elife03318f008",
                                        "elife03318f009", "elife03318f010",
                                        "elife03318f011", "elife03318f012",
                                        "elife03318f013", "elife03318f014",
                                        "elife03318f015", "elife03318f016"]
                        if href in gifs_03318 or href in gifs_02020:
                            extension = '.gif'
    
                    
                    # Add the file extension
                    tag.set('{http://www.w3.org/1999/xlink}href', href + extension)

        return root

    def change_media_video_id_in_xml(self, doi_id, root):
        """
        <media> tag id is changed,
        as well need to change rid attribute of matching xref tags
        """
        id_map = {}
        
        for media_tag in root.findall('.//media'):
            if media_tag.get('id'):
                old_id = media_tag.get('id')
                new_id = 'media' + str(re.sub('\D', '', old_id))
                # Save to the id map
                id_map[old_id] = new_id
                # Change the media tag id
                media_tag.set('id', new_id)
                
        # Change matching xref tags
        for xref_tag in root.findall('.//xref'):
            if xref_tag.get('rid'):
                # Some rid values may have more than one id separated by a space
                rids = xref_tag.get('rid').split(' ')
                for i, rid in enumerate(rids):
                    if rid in id_map.keys():
                        rids[i] = id_map[rid]
                xref_tag.set('rid', ' '.join(rids))
                    
        if len(id_map) > 0:
            if(self.logger):
                self.logger.info('media tag id replacements '
                                  + json.dumps(id_map) + ' in: ' + str(doi_id))                
        
        return root
    

    
    def author_keyword_replacements_in_xml(self, doi_id, root):
        """
        Using a separate file of keyword matches and replacements,
        match the lowercase version of the keyword, and if found
        replace with one or more new keywords
        """
        
        try:
            for kwd_group_tag in root.findall('./front/article-meta/kwd-group[@kwd-group-type="author-keywords"]'):
                for kwd_tag in kwd_group_tag.findall('.//kwd'):

                    tagged_text = ElementTree.tostring(kwd_tag)
                    tagged_text = tagged_text.replace('<kwd>','')
                    tagged_text = tagged_text.replace('</kwd>','')
                    # Remove extra whitespace
                    tagged_text = tagged_text.rstrip()
                    tagged_text = tagged_text.lower()
                    
                    if tagged_text in keywords.keys():
                        # Do the replacements
                        i = 0
                        for new_keyword in keywords[tagged_text]:
                            if i == 0:
                                # Change text of the existing tag for the first replacement
                                kwd_tag.text = new_keyword
                            else:
                                # More than one tag, append a new tag to the bottom
                                new_kwd_tag = SubElement(kwd_group_tag, "kwd")
                                new_kwd_tag.text = new_keyword
                                
                            i += 1

        except:
            if(self.logger):
                self.logger.error('something went wrong in the author keywords replacements '
                                  + doi_tag.text + ' in: ' + str(doi_id))
                    
        return root

    def author_keyword_en_rule_in_xml(self, doi_id, root):
        """
        
        """
        for kwd_tag in root.findall('./front/article-meta/kwd-group[@kwd-group-type="author-keywords"]/kwd'):
            if kwd_tag.text and '&#8211;' in kwd_tag.text:
                kwd_tag.text = kwd_tag.text.replace('&#8211;', '-')
        return root

 


    def remove_tag_from_tag_in_xml(self, parent_tag, tag_name):
        """
        Used in cleaning dodgy references
        """
        for tag in parent_tag.findall('.//' + tag_name):
            parent_tag.remove(tag)

    def related_article_convert_in_xml(self, root):
        """
        Remove id attribute from related-article tags
        """
        for tag in root.findall('.//related-article'):
            if tag.get('id'):
                del tag.attrib['id']
        return root
    
    def institution_university_convert_in_xml(self, root):
        """
        <institution content-type="university"> remove @content-type="university"
        Usually found in <award-group> <funding-source>
        """
        for tag in root.findall('.//institution'):
            if tag.get('content-type') and tag.get('content-type') == "university":
                del tag.attrib['content-type']
        return root

    def sub_article_title_convert_in_xml(self, root):
        """
        Standardise the sub-article titles
        """
        for tag in root.findall('./sub-article/front-stub/title-group/article-title'):
            if tag.text and tag.text.lower().startswith('decision'):
                tag.text = "Decision letter"
            elif tag.text and tag.text.lower().startswith('author'):
                tag.text = "Author response"
        return root

    def subject_group_convert_in_xml(self, root):
        """
        Convert capitalisation of <subject> tags in article categories
        """
        for tag in root.findall('./front/article-meta/article-categories/subj-group'):
            for subject_tag in tag.findall('./subject'):
                subject_tag.text = self.title_case(subject_tag.text)
        return root
    


    
    def research_organism_kwd_convert_in_xml(self, root, doi_id):
        """
        Convert capitalisation of <subject> tags in article categories
        Basic procedure,
          Look for research organisms kwd-group tag
          Read each kwd tag inside it, and get replacement XML if applicable
          Insert the new kwd tag 
          Remove the old kwd tag
        """
        for kwd_group_tag in root.findall('./front/article-meta/kwd-group[@kwd-group-type="research-organism"]'):

            # Start the insertion index where the first kwd element is found
            tag_index = xmlio.get_first_element_index(kwd_group_tag, 'kwd')
            
            for kwd_tag in kwd_group_tag.findall('.//kwd'):
                new_xml = self.new_research_organism_xml(self.kwd_xml_to_string_lower(kwd_tag))
                if not new_xml:
                    # No match returned, use the original value
                    new_xml = ElementTree.tostring(kwd_tag)
                    if(self.logger):
                        self.logger.info('no kwd replacement match for: ' + str(doi_id))
                        self.logger.info(new_xml)

                # Parse XML string into an XML element
                new_kwd_tag = ElementTree.fromstring(new_xml)
                # Insert the new tag
                kwd_group_tag.insert(tag_index, new_kwd_tag)
                # Remove the old tag
                kwd_group_tag.remove(kwd_tag)
                tag_index += 1

        return root

    def kwd_xml_to_string_lower(self, tag):
        """
        Given an Element, convert its contents to string,
        remove text for tags we do not want, convert it to lowercase
        and return it
        """
        tagged_text = ElementTree.tostring(tag)
        tagged_text = tagged_text.replace('<kwd>','')
        tagged_text = tagged_text.replace('</kwd>','')
        tagged_text = tagged_text.replace('<italic>','')
        tagged_text = tagged_text.replace('</italic>','')
        string_lower = tagged_text.lower().strip()
        return string_lower
    
    def new_research_organism_xml(self, string):
        """
        Given an lower case string of text only for a
        research organism kwd value, return a string
        of tagged XML as the replacment, otherwise return None
        """
        xml_string = None
        
        match_list = {}
        
        match_list['arabidopsis'] = '<kwd><italic>A. thaliana</italic></kwd>'
        match_list['bat'] = '<kwd>Bat</kwd>'
        match_list['b. subtilis'] = '<kwd><italic>B. subtilis</italic></kwd>'
        match_list['c. elegans'] = '<kwd><italic>C. elegans</italic></kwd>'
        match_list['c. intestinalis'] = '<kwd><italic>C. intestinalis</italic></kwd>'
        match_list['chicken'] = '<kwd>Chicken</kwd>'
        match_list['ciona intestinalis'] = '<kwd><italic>C. intestinalis</italic></kwd>'
        match_list['d. melanogaster'] = '<kwd><italic>D. melanogaster</italic></kwd>'
        match_list['dictyostelium'] = '<kwd><italic>Dictyostelium</italic></kwd>'
        match_list['drosophila melanogaster'] = '<kwd><italic>D. melanogaster</italic></kwd>'
        match_list['e. coli'] = '<kwd><italic>E. coli</italic></kwd>'
        match_list['frog'] = '<kwd>Frog</kwd>'
        match_list['fruit fly'] = '<kwd><italic>D. melanogaster</italic></kwd>'
        match_list['human'] = '<kwd>Human</kwd>'
        match_list['macaca mulatta'] = '<kwd>Rhesus macaque</kwd>'
        match_list['maize'] = '<kwd>Maize</kwd>'
        match_list['mouse'] = '<kwd>Mouse</kwd>'
        match_list['myceliophthora thermophila'] = '<kwd><italic>M. thermophila</italic></kwd>'
        match_list['n. crassa'] = '<kwd><italic>N. crassa</italic></kwd>'
        match_list['neurospora'] = '<kwd><italic>Neurospora</italic></kwd>'
        match_list['none'] = '<kwd>None</kwd>'
        match_list['oncopeltus fasciatus'] = '<kwd><italic>O. fasciatus</italic></kwd>'
        match_list['other'] = '<kwd>Other</kwd>'
        match_list['plasmodium falciparum'] = '<kwd><italic>P. falciparum</italic></kwd>'
        match_list['platynereis dumerilii'] = '<kwd><italic>P. dumerilii</italic></kwd>'
        match_list['rat'] = '<kwd>Rat</kwd>'
        match_list['s. cerevisiae'] = '<kwd><italic>S. cerevisiae</italic></kwd>'
        match_list['s. pombe'] = '<kwd><italic>S. pombe</italic></kwd>'
        match_list['salmonella enterica serovar typhi'] = '<kwd><italic>S. enterica</italic> serovar Typhi</kwd>'
        match_list['streptococcus pyogenes'] = '<kwd><italic>S. pyogenes</italic></kwd>'
        match_list['viruses'] = '<kwd>Virus</kwd>'
        match_list['volvox'] = '<kwd><italic>Volvox</italic></kwd>'
        match_list['xenopus'] = '<kwd><italic>Xenopus</italic></kwd>'
        match_list['yellow baboon (papio cynocephalus)'] = '<kwd><italic>P. cynocephalus</italic></kwd>'
        match_list['zebrafish'] = '<kwd>Zebrafish</kwd>'
        
        if match_list.get(string):
            xml_string = match_list.get(string)
        
        return xml_string

    def element_citation_collab_wrap_in_xml(self, root):
        """
        turn <element-citation><collab> into
        <element-citation><person-group person-group-type="author"><collab>
        """
        for citation_tag in root.findall('./back/ref-list/ref/element-citation'):
            person_group_tag = None
            if len(citation_tag.findall('./collab')) > 0:
                person_group_tag = Element("person-group")
                person_group_tag.set("person-group-type", "author")
                collab_tag_index = xmlio.get_first_element_index(citation_tag, 'collab')

            for collab_tag in citation_tag.findall('./collab'):

                new_collab_tag = SubElement(person_group_tag, "collab")
                new_collab_tag.text = collab_tag.text

                # Delete the old tag
                citation_tag.remove(collab_tag)
                
            # Insert the new person-group tag
            if person_group_tag is not None:
                citation_tag.insert( collab_tag_index - 1, person_group_tag)
                
        return root

    def title_case(self, string):
        ignore_words = ['and']
        word_list = string.split(' ')
        for i, word in enumerate(word_list):
            # Skip if the word if the first letter is a capital
            if word and word[0] == word[0].upper():
                continue
            if word.lower() not in ignore_words:
                word_list[i] = word.capitalize()
        return ' '.join(word_list)


    def create_new_zip(self, zip_file_name):
    
        new_zipfile = zipfile.ZipFile(self.ZIP_DIR + os.sep + zip_file_name,
                                      'w', zipfile.ZIP_DEFLATED, allowZip64 = True)
            
        dirfiles = self.file_list(self.OUTPUT_DIR)
        
        for df in dirfiles:
            filename = df.split(os.sep)[-1]
            new_zipfile.write(df, filename)
            
        new_zipfile.close()
    
    def clean_directories(self, full = False):
        """
        Deletes all the files from the activity directories
        in order to save on disk space immediately
        A full clean is only after all activities have finished,
        a non-full clean can be done after each article
        """
        for file in self.file_list(self.TMP_DIR):
            os.remove(file)
        for file in self.file_list(self.OUTPUT_DIR):
            os.remove(file)
        for file in self.file_list(self.JUNK_DIR):
            os.remove(file)
        for file in self.file_list(self.EPS_DIR):
            os.remove(file)
        for file in self.file_list(self.TIF_DIR):
            os.remove(file)

        if full is True:
            for file in self.file_list(self.ZIP_DIR):
                os.remove(file)
            for folder in self.folder_list(self.INPUT_DIR):
                for file in self.file_list(folder):
                    os.remove(file)

    
    def profile_article(self, input_dir, folder):
        """
        Temporary, profile the article by folder names in test data set
        In real code we still want this to return the same values
        """
        # Temporary setting of version values from directory names
        
        soup = self.article_soup(self.article_xml_file())
        
        # elife id / doi id / manuscript id
        fid = parser.doi(soup).split('.')[-1]
    
        # article status
        if parser.is_poa(soup) is True:
            status = 'poa'
        else:
            status = 'vor'
        
        # version
        version = self.version_number(input_dir, folder)
    
            
        return (fid, status, version)
    
    def max_poa_version_number_from_folders(self, input_dir):
        """
        Look at the folder names in the input_dir, and figure out
        the highest PoA version number based on their names
        """
        max_poa_version = None
        
        for folder_name in self.folder_list(input_dir):
            if '_' in self.folder_name_from_name(input_dir, folder_name):
                poa_version = self.folder_name_from_name(input_dir, folder_name).split('_v')[-1]
                if max_poa_version is None:
                    max_poa_version = int(poa_version)
                else:
                    if int(poa_version) > max_poa_version:
                        max_poa_version = int(poa_version)
        
        return max_poa_version
    
    def version_number(self, input_dir, folder):
        
        # Version depends on the folder of interest and
        #  all the folders for this article
        
        version_type = None
        vor_version = None
        poa_version = None
        max_poa_version = self.max_poa_version_number_from_folders(input_dir)
        
        # If the folder name contains underscore, then we want the PoA version number
        if '_' in self.folder_name_from_name(input_dir, folder):
            version_type = 'poa'
            if self.folder_name_from_name(input_dir, folder).split('_')[-1] == 'v1':
                poa_version = 1
            elif self.folder_name_from_name(input_dir, folder).split('_')[-1] == 'v2':
                poa_version = 2
            elif self.folder_name_from_name(input_dir, folder).split('_')[-1] == 'v3':
                poa_version = 3
            elif self.folder_name_from_name(input_dir, folder).split('_')[-1] == 'v4':
                poa_version = 4
        else:
            # We want the VoR version number
            version_type = 'vor'
                
        if max_poa_version is None and poa_version is None:
            vor_version = 1
        else:
            vor_version = max_poa_version + 1
        
        if(self.logger):
            self.logger.info('input_dir: ' + input_dir)
            self.logger.info('folder: ' + folder)
            self.logger.info('version_type: ' + str(version_type))
            self.logger.info('max_poa_version: ' + str(max_poa_version))
            self.logger.info('poa_version: ' + str(poa_version))
            self.logger.info('vor_version: ' + str(vor_version))
        
        if version_type == 'vor':
            return vor_version
        elif version_type == 'poa':
            return poa_version
        else:
            return None

    
    def article_xml_file(self):
        """
        Two directories the XML file might be in depending on the step
        """
        file_name = None
        
        for file_name in self.file_list(self.TMP_DIR):
            if file_name.endswith('.xml'):
                return file_name
        
        for file_name in self.file_list(self.OUTPUT_DIR):
            if file_name.endswith('.xml'):
                return file_name
            
        return file_name
    
    def article_soup(self, xml_filename):
        return parser.parse_document(xml_filename)






    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.TMP_DIR)
            os.mkdir(self.INPUT_DIR)
            os.mkdir(self.JUNK_DIR)
            os.mkdir(self.ZIP_DIR)
            os.mkdir(self.EPS_DIR)
            os.mkdir(self.TIF_DIR)
            os.mkdir(self.OUTPUT_DIR)
            
        except:
            pass