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

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

from elifetools import parseJATS as parser
from elifetools import xmlio

import boto.s3
from boto.s3.connection import S3Connection

import provider.s3lib as s3lib

"""
PublishFinalPOA activity
"""

class activity_PublishFinalPOA(activity.activity):
    
    def __init__(self, settings, logger, conn = None, token = None, activity_task = None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PublishFinalPOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 60 * 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout= 60 * 15
        self.description = "Download POA files from a bucket, zip each article separately, and upload to final bucket."
        
        # Local directory settings
        self.TMP_DIR = self.get_tmp_dir() + os.sep + "tmp_dir"
        self.INPUT_DIR = self.get_tmp_dir() + os.sep + "input_dir"
        self.OUTPUT_DIR = self.get_tmp_dir() + os.sep + "output_dir"
        self.JUNK_DIR = self.get_tmp_dir() + os.sep + "junk_dir"
        
        # Bucket for outgoing files
        self.input_bucket = settings.poa_packaging_bucket
        self.published_folder_prefix = "published/"
        self.published_folder_name = None
        
        self.publish_bucket = settings.publishing_buckets_prefix + settings.production_bucket
        
        # Track the success of some steps
        self.activity_status = None
        self.prepare_status = None
        self.approve_status = None
        self.publish_status = None
        
        # More file status tracking for reporting in email
        self.malformed_ds_file_names = []
        self.empty_ds_file_names = []
        self.unmatched_ds_file_names = []
    
    def do_activity(self, data = None):
        """
        Activity, do the work
        """
        if(self.logger):
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        
        # Create output directories
        self.create_activity_directories()
        
        # Set the published folder name
        # For now use todays date
        self.published_folder_name = (self.published_folder_prefix
                                      + str(datetime.datetime.utcnow().strftime('%Y%m%d'))
                                      + '/')
        
        self.prepare_status = self.check_published_folder_exists()
        
        if self.prepare_status:
            # Download the S3 objects
            self.download_files_from_s3()
        
        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()
        
        if self.approve_status is True:
            
            article_filenames_map = self.profile_article_files()
            
            for doi_id,filenames in article_filenames_map.iteritems():
                
                article_xml_file_name = self.article_xml_from_filename_map(filenames)

                new_filenames = self.new_filenames(doi_id, filenames)
                
                if article_xml_file_name:
                    xml_file = self.INPUT_DIR + os.sep + article_xml_file_name
                    self.convert_xml(doi_id, xml_file, filenames, new_filenames)
                    
                # TODO !!!!
                self.zip_article_files(doi_id, filenames, new_filenames)
                    
            # TODO!!!!
            self.publish_status = self.upload_files_to_s3()
            
        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Return the activity result, True or False
        result = True

        return result

    def new_filenames(self, doi_id, filenames):
        """
        Given a list of file names for one article,
        rename them
        Since there should only be one xml, pdf and possible zip
        this should be simple
        """
        new_filenames = []
        for filename in filenames:
            name_prefix = 'elife-' + str(doi_id).zfill(5)
            if filename.endswith('.xml'):
                new_filenames.append(name_prefix + '.xml')
            if filename.endswith('.pdf'):
                new_filenames.append(name_prefix + '.pdf')
            if filename.endswith('.zip'):
                new_filenames.append(name_prefix + '-supp.zip')
        return new_filenames
        

    def profile_article_files(self):
        """
        In the inbox, look for each article doi_id
        and the files associated with that article
        """
        article_filenames_map = {}
        
        for file in glob.glob(self.INPUT_DIR + '/*'):
            filename = file.split(os.sep)[-1]
            doi_id = self.doi_id_from_filename(filename)
            if doi_id:
                #doi_id_str = str(doi_id).zfill(5)
                if doi_id not in article_filenames_map:
                    article_filenames_map[doi_id] = []
                # Add the filename to the map for this article
                article_filenames_map[doi_id].append(filename)
        
        return article_filenames_map
        
    def doi_id_from_filename(self, filename):
        """
        From a filename, get the doi_id portion
        Example file names
            decap_elife_poa_e10727.pdf
            decap_elife_poa_e12029v2.pdf
            elife_poa_e10727.xml
            elife_poa_e10727_ds.zip
            elife_poa_e12029v2.xml
        """
        if filename is None:
            return None
        
        doi_id = None
        # Remove folder names, if present
        filename = filename.split(os.sep)[-1]
        part = filename.replace('decap_elife_poa_e', '')
        part = part.replace('elife_poa_e', '')
        # Take the next five characters as digits
        try:
            doi_id = int(part[0:4])
        except:
            doi_id = None
        return doi_id
        
        
    def article_xml_from_filename_map(self, filenames):
        """
        Given a list of file names, return the article xml file name
        """
        for f in filenames:
            if f.endswith('.xml'):
                return f
        return None

    def convert_xml(self, doi_id, xml_file, filenames, new_filenames):

        # Register namespaces
        xmlio.register_xmlns()
        
        root = xmlio.parse(xml_file)

        soup = self.article_soup(xml_file)

        if parser.is_poa(soup):
            if parser.pub_date(soup) is None:
                # add the published date to the XML
                root = self.add_pub_date_to_xml(doi_id, root)
            
            # set the article-id, to overwrite the v2, v3 value if present
            root = self.set_article_id_xml(doi_id, root)
            
            # if ds.zip file is there, then add it to the xml
            poa_ds_zip_file = None
            for f in new_filenames:
                if f.endswith('.zip'):
                    poa_ds_zip_file = f
            if poa_ds_zip_file:
                root = self.add_poa_ds_zip_to_xml(doi_id, poa_ds_zip_file, root)
            
                
        # Start the file output
        reparsed_string = xmlio.output(root)

        # Remove extra whitespace here for PoA articles to clean up and one VoR file too
        reparsed_string = reparsed_string.replace("\n",'').replace("\t",'')
        
        f = open(xml_file, 'wb')
        f.write(reparsed_string)
        f.close()
       
    def article_soup(self, xml_file):
        return parser.parse_document(xml_file) 

    def add_pub_date_to_xml(self, doi_id, root):
        
        # Get the date for the first version
        date_struct = None
        date_str = self.get_pub_date_from_lax(doi_id)
        
        if date_str is not None:
            date_struct = time.strptime(date_str,  "%Y%m%d000000")
        else:
            # Use current date
            date_struct = time.gmtime()
        
        # Create the pub-date XML tag
        pub_date_tag = self.pub_date_xml_element(date_struct)

        # Add the tag to the XML
        for tag in root.findall('./front/article-meta'):
            parent_tag_index = xmlio.get_first_element_index(tag, 'elocation-id')
            if not parent_tag_index:
                if(self.logger):
                    self.logger.info('no elocation-id tag and no pub-date added: ' + str(doi_id))
            else:
                tag.insert( parent_tag_index - 1, pub_date_tag)
                
            # Should only do it once but ensure it is only done once
            break
        
        return root
    
    def pub_date_xml_element(self, pub_date):
        
        pub_date_tag = Element("pub-date")
        pub_date_tag.set("publication-format", "electronic")
        pub_date_tag.set("date-type", "pub")
        
        day = SubElement(pub_date_tag, "day")
        day.text = str(pub_date.tm_mday).zfill(2)
        
        month = SubElement(pub_date_tag, "month")
        month.text = str(pub_date.tm_mon).zfill(2)
        
        year = SubElement(pub_date_tag, "year")
        year.text = str(pub_date.tm_year)
    
        return pub_date_tag
    
    def set_article_id_xml(self, doi_id, root):
        
        for tag in root.findall('./front/article-meta/article-id'):
            if tag.get('pub-id-type') == "publisher-id":
                # Overwrite the text with the base DOI value
                tag.text = str(doi_id).zfill(5)
                
        return root

    def add_poa_ds_zip_to_xml(self, doi_id, file_name, root):
        """
        Add the ext-link tag to the XML for the PoA ds.zip file
        """

        # Create the XML tag
        supp_tag = self.ds_zip_xml_element(file_name, doi_id)

        # Add the tag to the XML
        for tag in root.findall('./front/article-meta'):
            parent_tag_index = xmlio.get_first_element_index(tag, 'history')
            if not parent_tag_index:
                if(self.logger):
                    self.logger.info('no history tag and no ds_zip tag added: ' + str(doi_id))
            else:
                tag.insert( parent_tag_index - 1, supp_tag)
            
        return root

    def ds_zip_xml_element(self, file_name, doi_id):
        
        supp_tag = Element("supplementary-material")
        ext_link_tag = SubElement(supp_tag, "ext-link")
        ext_link_tag.set("xlink:href", file_name)
        if 'supp' in file_name:
            ext_link_tag.text = "Download zip"
            
            p_tag = SubElement(supp_tag, "p")
            p_tag.text = "Any figures and tables for this article are included in the PDF. The zip folder contains additional supplemental files."

        return supp_tag

    def get_pub_date_from_lax(self, doi_id):
        # TODO !!!!
        pass
    
    def zip_article_files(self, doi_id, filenames, new_filenames):
        # TODO !!!!
        pass

    def upload_files_to_s3(self):
        # TODO !!!!
        pass

    def check_published_folder_exists(self):
        
        if not self.published_folder_name:
            return None
        
        bucket_name = self.input_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        
        # Strip the trailing slash from the folder name if present
        published_folder_prefix = self.published_folder_name.rstrip('/')
        
        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket          = bucket,
            key_type        = 'prefix',
            prefix          = published_folder_prefix)
        
        if len(s3_key_names) > 0:
            return True
        else:
            return False

    def download_files_from_s3(self):
        """
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml and .pdf files to be bundled.
        """
        
        file_extensions = []
        file_extensions.append(".xml")
        file_extensions.append(".pdf")
        file_extensions.append(".zip")
        
        bucket_name = self.input_bucket
        
        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket          = bucket,
            prefix          = self.published_folder_name,
            file_extensions = file_extensions)

        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            filename_plus_path = self.INPUT_DIR + os.sep + filename
            
            if(self.logger):
                self.logger.info('PublishFinalPOA downloading: %s' % filename_plus_path)
        
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()
        

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the FTP endpoint
        Check for empty made_ftp_ready_dir
        Also, remove files that should not be uploaded due to incomplete
        sets of files per article
        """

        status = None

        # Check for empty directory
        if len(glob.glob(self.INPUT_DIR)) <= 0:
            status = False
        else:
            status = True

        # For each data supplements file, move invalid ones to not publish by FTP
        file_type = "/*_ds.zip"
        zipfiles = glob.glob(self.INPUT_DIR + file_type)
        for input_zipfile in zipfiles:
            badfile = None
            
            try:
                current_zipfile = zipfile.ZipFile(input_zipfile, 'r')
            except:
                badfile = True
                self.malformed_ds_file_names.append(input_zipfile)
                current_zipfile = None

            if current_zipfile:
                # Check for those with missing or empty manifest.xml
                if self.manifest_xml_not_empty(current_zipfile) is not True:
                    badfile = True
                    self.malformed_ds_file_names.append(current_zipfile.filename)
    
                # Check for those with no zipped folder contents
                if self.check_empty_supplemental_files(current_zipfile) is not True:
                    badfile = True
                    self.empty_ds_file_names.append(current_zipfile.filename)
    
                # Check for a file with no matching XML document
                if (self.check_matching_xml_file(current_zipfile) is not True or
                    self.check_matching_pdf_file(current_zipfile) is not True):
                    badfile = True
                    self.unmatched_ds_file_names.append(current_zipfile.filename)
                    
                current_zipfile.close()
                
            if badfile:
                # File is not good, move it somewhere
                shutil.move(input_zipfile, self.JUNK_DIR + "/")
                
        # For each xml or pdf file, check there is a matching pair
        xml_file_type = "/*.xml"
        pdf_file_type = "/*.pdf"
        xml_files = glob.glob(self.INPUT_DIR + xml_file_type)
        pdf_files = glob.glob(self.INPUT_DIR + pdf_file_type)
        
        for filename in xml_files:
            matching_filename = self.get_filename_from_path(filename, ".xml")
            pdf_filenames = map(lambda f: self.get_filename_from_path(f, ".pdf"), pdf_files)
            pdf_filenames = map(lambda f: f.replace('decap_', ''), pdf_filenames)
            if matching_filename not in pdf_filenames:
                shutil.move(filename, self.JUNK_DIR + "/")
                
        for filename in pdf_files:
            matching_filename = self.get_filename_from_path(filename, ".pdf")
            matching_filename = matching_filename.replace('decap_', '')
            xml_filenames = map(lambda f: self.get_filename_from_path(f, ".xml"), xml_files)
            if matching_filename not in xml_filenames:
                shutil.move(filename, self.JUNK_DIR + "/")
            
        return status
    
    def manifest_xml_not_empty(self, input_zipfile):
        """
        Given a zipfile.ZipFile object, check if it contains a
        manifest.xml file and it is non-empty (has a size greater than zero)
        """
        manifest = None
        try:
            manifest = input_zipfile.read("manifest.xml")
        except:
            return False
        
        if manifest:
            if len(str(manifest)) > 0:
                # Has some content
                return True
            else:
                return False
        else:
            return False
        
        # Default return
        return None
    
    def check_empty_supplemental_files(self, input_zipfile):
        """
        Given a zipfile.ZipFile object, look inside the internal zipped folder
        and asses the zipextfile object length to see whether it is empty
        """
        zipextfile_line_count = 0
        sub_folder_name = None
    
        for name in input_zipfile.namelist():
            if re.match("^.*\.zip$", name):
                sub_folder_name = name
                
        if sub_folder_name:
            zipextfile = input_zipfile.open(sub_folder_name)
        
            while zipextfile.readline():
                zipextfile_line_count += 1

        # Empty subfolder zipextfile object will have only 1 line
        #  Non-empty file will have more than 1 line
        if zipextfile_line_count <= 1:
            return False
        elif zipextfile_line_count > 1:
            return True

    def check_matching_xml_file(self, input_zipfile):
        """
        Given a zipfile.ZipFile object, check if for the DOI it represents
        there is a matching XML file for that DOI
        """
        zip_file_article_number = self.get_filename_from_path(input_zipfile.filename, "_ds.zip")
        #print zip_file_article_number

        file_type = "/*.xml"
        xml_files = glob.glob(self.INPUT_DIR + file_type)
        xml_file_articles_numbers = []
        for f in xml_files: xml_file_articles_numbers.append(self.get_filename_from_path(f, ".xml"))
        #print xml_file_articles_numbers
        
        if zip_file_article_number in xml_file_articles_numbers:
            return True

        # Default return
        return False

    def check_matching_pdf_file(self, input_zipfile):
        """
        Given a zipfile.ZipFile object, check if for the DOI it represents
        there is a matching PDF file for that DOI
        """
        zip_file_article_number = self.get_filename_from_path(input_zipfile.filename, "_ds.zip")

        file_type = "/*.pdf"
        pdf_files = glob.glob(self.INPUT_DIR + file_type)
        pdf_file_articles_numbers = []
        for f in pdf_files:
            pdf_file_name = self.get_filename_from_path(f, ".pdf")
            # Remove the decap_ from the start of the file name before comparing
            pdf_file_name = pdf_file_name.replace('decap_', '')
            pdf_file_articles_numbers.append(pdf_file_name)
        
        if zip_file_article_number in pdf_file_articles_numbers:
            return True

        # Default return
        return False


        
    def get_filename_from_path(self, f, extension):
        """
        Get a filename minus the supplied file extension
        and without any folder or path
        """
        filename = f.split(extension)[0]
        # Remove path if present
        try:
            filename = filename.split(os.sep)[-1]
        except:
            pass
        
        return filename
        

        
    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.TMP_DIR)
            os.mkdir(self.INPUT_DIR)
            os.mkdir(self.OUTPUT_DIR)
            os.mkdir(self.JUNK_DIR)
            
        except:
            pass