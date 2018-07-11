import os
import boto.swf
import json
import datetime
import time

import zipfile
import requests
import glob
import shutil
import re

import activity

from xml.etree.ElementTree import Element, SubElement

from elifetools import parseJATS as parser
from elifetools import xmlio

import boto.s3
from boto.s3.connection import S3Connection

import provider.s3lib as s3lib
import provider.simpleDB as dblib
import provider.lax_provider as lax_provider

"""
PublishFinalPOA activity
"""

class activity_PublishFinalPOA(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "PublishFinalPOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 60 * 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = ("Download POA files from a bucket, zip each article separately, "
                            + "and upload to final bucket.")

        # Local directory settings
        self.TMP_DIR = self.get_tmp_dir() + os.sep + "tmp_dir"
        self.INPUT_DIR = self.get_tmp_dir() + os.sep + "input_dir"
        self.OUTPUT_DIR = self.get_tmp_dir() + os.sep + "output_dir"
        self.JUNK_DIR = self.get_tmp_dir() + os.sep + "junk_dir"
        self.DONE_DIR = self.get_tmp_dir() + os.sep + "done_dir"

        # Bucket for outgoing files
        self.input_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "outbox/"
        self.published_folder_prefix = "published/"
        self.published_folder_name = None

        self.publish_bucket = settings.publishing_buckets_prefix + settings.production_bucket

        # Track the success of some steps
        self.activity_status = None
        self.approve_status = None
        self.publish_status = None

        # More file status tracking for reporting in email
        self.outbox_s3_key_names = []
        self.malformed_ds_file_names = []
        self.empty_ds_file_names = []
        self.unmatched_ds_file_names = []

        # Data provider where email body is saved
        self.db = dblib.SimpleDB(settings)

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.create_activity_directories()

        # Set the published folder name as todays date
        self.published_folder_name = (self.published_folder_prefix
                                      + str(datetime.datetime.utcnow().strftime('%Y%m%d'))
                                      + '/')

        # Download the S3 objects
        self.download_files_from_s3()

        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()

        self.done_xml_files = []
        self.clean_from_outbox_files = []

        if self.approve_status is True:

            article_filenames_map = self.profile_article_files()

            for doi_id, filenames in article_filenames_map.iteritems():

                article_xml_file_name = self.article_xml_from_filename_map(filenames)

                new_filenames = self.new_filenames(doi_id, filenames)

                if article_xml_file_name:
                    xml_file = self.INPUT_DIR + os.sep + article_xml_file_name

                    try:
                        self.convert_xml(doi_id, xml_file, filenames, new_filenames)
                    except Exception as e:
                        # One possible error is an entirely blank XML file or a malformed xml file
                        if self.logger:
                            self.logger.exception("Exception when converting XML for doi %s, %s" %
                                                  (str(doi_id), e.message))
                        continue

                revision = self.next_revision_number(doi_id)
                zip_file_name = self.new_zip_file_name(doi_id, revision)
                if revision and zip_file_name:
                    self.zip_article_files(doi_id, filenames, new_filenames, zip_file_name)
                    # Add files to the lists to be processed after
                    new_article_xml_file_name = self.article_xml_from_filename_map(new_filenames)
                    self.done_xml_files.append(new_article_xml_file_name)
                    self.clean_from_outbox_files = self.clean_from_outbox_files + filenames

            # Upload the zip files to the publishing bucket
            self.publish_status = self.upload_files_to_s3()

        # Clean the outbox
        if len(self.clean_from_outbox_files) > 0:
            self.clean_outbox(self.published_folder_name, self.clean_from_outbox_files)

        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Send email
        self.add_email_to_queue()

        # Return the activity result, True or False
        result = True

        if self.activity_status is True:
            self.clean_tmp_dir()

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
            doi_id = int(part[0:5])
        except (IndexError, ValueError):
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

        root, doctype_dict = xmlio.parse(xml_file, return_doctype_dict=True)

        soup = self.article_soup(xml_file)

        if parser.is_poa(soup):
            pub_date = None
            if parser.pub_date(soup) is None:
                # add the published date to the XML
                pub_date = self.get_pub_date_if_missing(doi_id)
                root = self.add_pub_date_to_xml(doi_id, pub_date, root)
            else:
                pub_date = parser.pub_date(soup)

            if parser.volume(soup) is None:
                # Get the pub-date year to calculate the volume
                year = pub_date[0]
                volume = year - 2011
                self.add_volume_to_xml(doi_id, volume, root)

            # set the article-id, to overwrite the v2, v3 value if present
            root = self.set_article_id_xml(doi_id, root)

            # if pdf file then add self-uri tag
            if parser.self_uri(soup) is not None and len(parser.self_uri(soup)) == 0:
                for filename in new_filenames:
                    if filename.endswith('.pdf'):
                        root = self.add_self_uri_to_xml(doi_id, filename, root)

            # if ds.zip file is there, then add it to the xml
            poa_ds_zip_file = None
            for f in new_filenames:
                if f.endswith('.zip'):
                    poa_ds_zip_file = f
            if poa_ds_zip_file:
                root = self.add_poa_ds_zip_to_xml(doi_id, poa_ds_zip_file, root)


        # Start the file output
        reparsed_string = xmlio.output(root, type=None, doctype_dict=doctype_dict)

        # Remove extra whitespace here for PoA articles to clean up and one VoR file too
        reparsed_string = reparsed_string.replace("\n", '').replace("\t", '')

        f = open(xml_file, 'wb')
        f.write(reparsed_string)
        f.close()

    def article_soup(self, xml_file):
        return parser.parse_document(xml_file)

    def add_tag_to_xml_before_elocation_id(self, add_tag, root, doi_id=""):
        # Add the tag to the XML
        for tag in root.findall('./front/article-meta'):
            parent_tag_index = xmlio.get_first_element_index(tag, 'elocation-id')
            if not parent_tag_index:
                if self.logger:
                    self.logger.info('no elocation-id tag and no '
                                     + str(add_tag.tag) + ' added: ' + str(doi_id))
            else:
                tag.insert(parent_tag_index - 1, add_tag)

            # Should only do it once but ensure it is only done once
            break
        return root

    def get_pub_date_if_missing(self, doi_id):
        # Get the date for the first version
        date_struct = None
        date_str = self.get_pub_date_str_from_lax(doi_id)

        if date_str is not None:
            date_struct = time.strptime(date_str, "%Y%m%d000000")
        else:
            # Use current date
            date_struct = time.gmtime()
        return date_struct

    def add_pub_date_to_xml(self, doi_id, date_struct, root):
        # Create the pub-date XML tag
        pub_date_tag = self.pub_date_xml_element(date_struct)
        root = self.add_tag_to_xml_before_elocation_id(pub_date_tag, root, doi_id)
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

    def add_volume_to_xml(self, doi_id, volume, root):
        # Create the pub-date XML tag
        volume_tag = self.volume_xml_element(volume)
        root = self.add_tag_to_xml_before_elocation_id(volume_tag, root, doi_id)
        return root

    def volume_xml_element(self, volume):
        volume_tag = Element("volume")
        volume_tag.text = str(volume)
        return volume_tag

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
        back_sec_tags = root.findall('./back/sec[@sec-type="supplementary-material"]')
        if not back_sec_tags:
            # add sec tag
            back_tags = root.findall('./back')
            back_tag = back_tags[0]
            sec_tag = SubElement(back_tag, "sec")
            sec_tag.set("sec-type", "supplementary-material")
        else:
            sec_tag = back_sec_tags[-1]

        sec_tag.append(supp_tag)

        return root

    def ds_zip_xml_element(self, file_name, doi_id):

        supp_tag = Element("supplementary-material")
        ext_link_tag = SubElement(supp_tag, "ext-link")
        ext_link_tag.set("xlink:href", file_name)
        if 'supp' in file_name:
            ext_link_tag.text = "Download zip"

            p_tag = SubElement(supp_tag, "p")
            p_tag.text = ("Any figures and tables for this article are included "
                          + "in the PDF. The zip folder contains additional supplemental files.")

        return supp_tag

    def add_self_uri_to_xml(self, doi_id, file_name, root):
        """
        Add the self-uri tag to the XML for the PDF file
        """

        # Create the XML tag
        self_uri_tag = self.self_uri_xml_element(file_name, doi_id)

        # Add the tag to the XML
        for tag in root.findall('./front/article-meta'):
            parent_tag_index = xmlio.get_first_element_index(tag, 'permissions')
            if not parent_tag_index:
                if self.logger:
                    self.logger.info('no permissions tag and no self-uri tag added: ' + str(doi_id))
            else:
                tag.insert(parent_tag_index, self_uri_tag)

        return root

    def self_uri_xml_element(self, file_name, doi_id):
        self_uri_tag = Element("self-uri")
        self_uri_tag.set("content-type", "pdf")
        self_uri_tag.set("xlink:href", file_name)
        return self_uri_tag

    def get_pub_date_str_from_lax(self, doi_id):
        """
        Check lax for any article published version
        If found, get the pub date and format it as a string YYYYMMDDhhmmss
        """
        article_id = str(doi_id).zfill(5)
        return lax_provider.article_publication_date(article_id, self.settings, self.logger)

    def next_revision_number(self, doi_id, status='poa'):
        """
        From the bucket, get a list of zip files
        and determine the next revision number to use
        """
        next_revision_number = 1

        bucket_name = self.publish_bucket

        file_extensions = []
        file_extensions.append(".zip")

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(bucket=bucket)

        max_revision_number = 0
        for key_name in s3_key_names:

            name_prefix = 'elife-' + str(doi_id).zfill(5) + '-' + str(status) + '-r'
            if key_name.startswith(name_prefix):
                # Attempt to get a revision number from the matching files
                try:
                    part = key_name.replace(name_prefix, '')
                    revision = int(part.split('.')[0])
                except (IndexError, ValueError):
                    revision = None
                if revision and revision > max_revision_number:
                    max_revision_number = revision

        if max_revision_number > 0:
            next_revision_number = max_revision_number + 1

        return next_revision_number

    def new_zip_file_name(self, doi_id, revision, status='poa'):
        new_file_name = None

        new_file_name = ('elife-' + str(doi_id).zfill(5)
                         + '-' + str(status)
                         + '-r' + str(revision)
                         + '.zip')

        return new_file_name

    def zip_article_files(self, doi_id, filenames, new_filenames, zip_filename):
        """
        Move the files from old to new name into the tmp_dir
        add them to a zip file
        and move the zip file to the output_dir
        """

        # Move the files
        for filename in filenames:
            new_filename = self.new_filename_from_old(filename, new_filenames)
            if new_filename:
                old_filename_plus_path = self.INPUT_DIR + os.sep + filename
                new_filename_plus_path = self.TMP_DIR + os.sep + new_filename
                if self.logger:
                    self.logger.info('moving poa file from %s to %s'
                                     % (old_filename_plus_path, new_filename_plus_path))

                shutil.move(old_filename_plus_path, new_filename_plus_path)

        # Repackage the PoA ds zip file
        self.repackage_poa_ds_zip()

        # Create the zip
        zip_filename_plus_path = self.OUTPUT_DIR + os.sep + zip_filename
        new_zipfile = zipfile.ZipFile(zip_filename_plus_path,
                                      'w', zipfile.ZIP_DEFLATED, allowZip64=True)

        # Add the files
        for file in glob.glob(self.TMP_DIR + '/*'):
            filename = file.split(os.sep)[-1]
            new_zipfile.write(file, filename)
        new_zipfile.close()

        # Clean out the tmp_dir
        for file in glob.glob(self.TMP_DIR + '/*'):
            filename = file.split(os.sep)[-1]
            new_filename_plus_path = self.DONE_DIR + os.sep + filename
            shutil.move(file, new_filename_plus_path)

    def repackage_poa_ds_zip(self):
        """
        If there is a ds zip file for this article files in the tmp_dir
        then repackage it
        """
        zipfiles = glob.glob(self.TMP_DIR + '/*.zip')
        if len(zipfiles) == 1:
            zipfile_file = zipfiles[0]
            zipfile_filename = zipfile_file.split(os.sep)[-1]
            myzip = zipfile.ZipFile(zipfile_file, 'r')
            # New style zip file, if no manifest.xml file then leave the zip file alone
            if 'manifest.xml' not in myzip.namelist():
                myzip.close()
                return

            # Extract the zip
            myzip.extractall(self.TMP_DIR)
            myzip.close()

            # Remove the manifest.xml file
            try:
                shutil.move(self.TMP_DIR + os.sep + 'manifest.xml',
                            self.JUNK_DIR + os.sep + 'manifest.xml')
                if self.logger:
                    self.logger.info("moving PoA zip manifest.xml to the junk folder")
            except IOError:
                pass

            # Move the old zip file
            zipfiles_now = glob.glob(self.TMP_DIR + '/*.zip')
            for new_zipfile in zipfiles_now:
                if not new_zipfile.endswith('_Supplemental_files.zip'):
                    # Old zip file, move it to junk
                    new_zipfile_filename = new_zipfile.split(os.sep)[-1]
                    shutil.move(new_zipfile, self.JUNK_DIR + os.sep + new_zipfile_filename)

            # Then can rename the new zip file
            zipfiles_now = glob.glob(self.TMP_DIR + '/*.zip')
            for new_zipfile in zipfiles_now:
                if new_zipfile.endswith('_Supplemental_files.zip'):
                    # Rename the zip as the old zip
                    shutil.move(new_zipfile, self.TMP_DIR + os.sep + zipfile_filename)


    def new_filename_from_old(self, old_filename, new_filenames):
        """
        From a list of new file names, find the new name
        that corresponds with the old file name based on the file extension
        """
        new_filename = None
        try:
            extension = old_filename.split('.')[-1]
        except IndexError:
            extension = None
        if extension:
            for filename in new_filenames:
                try:
                    new_extension = filename.split('.')[-1]
                except IndexError:
                    new_extension = None
                if new_extension and extension == new_extension:
                    new_filename = filename
        return new_filename

    def upload_files_to_s3(self):
        """
        Upload the article zip files to S3
        """

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        for file in glob.glob(self.OUTPUT_DIR + '/*.zip'):
            s3_key_name = file.split(os.sep)[-1]
            s3key = boto.s3.key.Key(bucket)
            s3key.key = s3_key_name
            s3key.set_contents_from_filename(file, replace=True)
            if self.logger:
                self.logger.info("uploaded " + s3_key_name + " to s3 bucket " + bucket_name)
        return True

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

        s3_key_names = s3lib.get_s3_key_names_from_bucket(bucket=bucket,
                                                          prefix=self.outbox_folder,
                                                          file_extensions=file_extensions)
        self.outbox_s3_key_names = s3_key_names

        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            filename_plus_path = self.INPUT_DIR + os.sep + filename

            if self.logger:
                self.logger.info('PublishFinalPOA downloading: %s' % filename_plus_path)

            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()


    def approve_for_publishing(self):
        """
        Final checks before processing the downloaded files
        Check for empty INPUT_DIR
        Also, remove files that should not be published due to incomplete
        sets of files per article
        """

        status = None

        # Check for empty directory
        if len(glob.glob(self.INPUT_DIR + "/*")) <= 1:
            status = False
        else:
            status = True

        # For each data supplements file, move invalid ones to not publish by FTP
        file_type = "/*_ds.zip"
        zipfiles = glob.glob(self.INPUT_DIR + file_type)
        for input_zipfile in zipfiles:
            badfile = None
            filename = input_zipfile.split(os.sep)[-1]
            try:
                current_zipfile = zipfile.ZipFile(input_zipfile, 'r')
            except zipfile.BadZipfile:
                badfile = True
                self.malformed_ds_file_names.append(filename)
                current_zipfile = None

            if current_zipfile:
                filename = current_zipfile.filename.split(os.sep)[-1]
                # Check for those with no zipped folder contents
                if self.check_empty_supplemental_files(current_zipfile) is not True:
                    badfile = True
                    self.empty_ds_file_names.append(filename)

                # Check for a file with no matching XML document
                if (self.check_matching_xml_file(filename) is not True or
                        self.check_matching_pdf_file(filename) is not True):
                    badfile = True
                    self.unmatched_ds_file_names.append(filename)

                current_zipfile.close()

            if badfile:
                # File is not good, move it somewhere
                shutil.move(self.INPUT_DIR + os.sep + filename, self.JUNK_DIR + "/")

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
        except KeyError:
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
        and assess the zipextfile object length to see whether it is empty
        """
        zipextfile_line_count = 0
        sub_folder_name = None

        for name in input_zipfile.namelist():
            if re.match(r"^.*\.zip$", name):
                sub_folder_name = name

        # skip this check if there is no internal zip file
        if not sub_folder_name and len(input_zipfile.namelist()) > 0:
            return True

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

    def check_matching_xml_file(self, zip_filename):
        """
        Given a zipfile.ZipFile object, check if for the DOI it represents
        there is a matching XML file for that DOI
        """
        zip_file_article_number = self.get_filename_from_path(zip_filename, "_ds.zip")

        file_type = "/*.xml"
        xml_files = glob.glob(self.INPUT_DIR + file_type)
        xml_file_articles_numbers = []
        for f in xml_files:
            xml_file_articles_numbers.append(self.get_filename_from_path(f, ".xml"))
        #print xml_file_articles_numbers

        if zip_file_article_number in xml_file_articles_numbers:
            return True

        # Default return
        return False

    def check_matching_pdf_file(self, zip_filename):
        """
        Given a zipfile.ZipFile object, check if for the DOI it represents
        there is a matching PDF file for that DOI
        """
        zip_file_article_number = self.get_filename_from_path(zip_filename, "_ds.zip")

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


    def clean_outbox(self, published_folder_name, outbox_files):
        """
        Move files from S3 outbox to the published folder
        """
        bucket_name = self.input_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        for file_name in outbox_files:
            old_s3_key_name = self.outbox_folder + file_name
            new_s3_key_name = published_folder_name + file_name

            # First copy
            new_s3_key = None
            try:
                new_s3_key = bucket.copy_key(new_s3_key_name, bucket_name, old_s3_key_name)
            except:
                pass

            # Then delete the old key if successful
            if isinstance(new_s3_key, boto.s3.key.Key):
                old_s3_key = bucket.get_key(old_s3_key_name)
                old_s3_key.delete()


    def get_filename_from_path(self, f, extension):
        """
        Get a filename minus the supplied file extension
        and without any folder or path
        """
        filename = f.split(extension)[0]
        # Remove path if present
        try:
            filename = filename.split(os.sep)[-1]
        except IndexError:
            pass

        return filename


    def add_email_to_queue(self):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        # Connect to DB
        db_conn = self.db.connect()

        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()

        body = self.get_email_body(current_time)
        subject = self.get_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if type(self.settings.ses_poa_recipient_email) == list:
            for email in self.settings.ses_poa_recipient_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_poa_recipient_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            self.db.elife_add_email_to_email_queue(
                recipient_email=email,
                sender_email=sender_email,
                email_type="PublishFinalPOA",
                format="text",
                subject=subject,
                body=body)

        return True

    def get_activity_status_text(self, activity_status):
        """
        Given the activity status boolean, return a human
        readable text version
        """
        if activity_status is True:
            activity_status_text = "Success!"
        else:
            activity_status_text = "FAILED."

        return activity_status_text

    def get_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        # Count the files moved from the outbox, the files that were processed
        files_count = 0
        if self.outbox_s3_key_names:
            files_count = len(self.outbox_s3_key_names)

        subject = (self.name + " " + activity_status_text +
                   " files: " + str(files_count) +
                   ", " + datetime_string +
                   ", eLife SWF domain: " + self.settings.domain)

        return subject

    def get_email_body(self, current_time):
        """
        Format the body of the email
        """

        body = ""

        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"

        body += "activity_status: " + str(self.activity_status) + "\n"
        body += "approve_status: " + str(self.approve_status) + "\n"
        body += "publish_status: " + str(self.publish_status) + "\n"

        body += "\n"
        body += "Outbox files: " + "\n"

        files_count = 0
        if self.outbox_s3_key_names:
            files_count = len(self.outbox_s3_key_names)
        if files_count > 0:
            for name in self.outbox_s3_key_names:
                body += name + "\n"
        else:
            body += "No files in outbox." + "\n"

        if files_count > 0:
            # Report on any empty or unmatched supplement files
            if len(self.malformed_ds_file_names) > 0:
                body += "\n"
                body += "Note: Malformed ds files not sent by ftp: " + "\n"
                for name in self.malformed_ds_file_names:
                    body += name + "\n"
            if len(self.empty_ds_file_names) > 0:
                body += "\n"
                body += "Note: Empty ds files not sent by ftp: " + "\n"
                for name in self.empty_ds_file_names:
                    body += name + "\n"
            if len(self.unmatched_ds_file_names) > 0:
                body += "\n"
                body += "Note: Unmatched ds files not sent by ftp: " + "\n"
                for name in self.unmatched_ds_file_names:
                    body += name + "\n"

        if self.publish_status is True and files_count > 0:
            body += "\n"
            body += "Files moved to: " + str(self.published_folder_name) + "\n"

        for name in self.clean_from_outbox_files:
            body += name + "\n"

        body += "\n"
        body += "-------------------------------\n"
        body += "SWF workflow details: " + "\n"
        body += "activityId: " + str(self.get_activityId()) + "\n"
        body += "As part of workflowId: " + str(self.get_workflowId()) + "\n"
        body += "As at " + datetime_string + "\n"
        body += "Domain: " + self.settings.domain + "\n"

        body += "\n"

        body += "\n\nSincerely\n\neLife bot"

        return body


    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.TMP_DIR)
            os.mkdir(self.INPUT_DIR)
            os.mkdir(self.OUTPUT_DIR)
            os.mkdir(self.JUNK_DIR)
            os.mkdir(self.DONE_DIR)

        except OSError:
            pass
