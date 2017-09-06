import os
import json
import zipfile
import glob
import shutil

from ftplib import FTP
import ftplib

import activity

from boto.s3.connection import S3Connection

import provider.s3lib as s3lib
import provider.sftp as sftplib
import provider.article_processing as article_processing

from elifetools import parseJATS as parser

"""
FTPArticle activity
"""

class activity_FTPArticle(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "FTPArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = "Download VOR files and publish by FTP to some particular place."

        # Bucket settings
        self.article_bucket = settings.bucket
        self.pmc_zip_bucket = settings.poa_packaging_bucket
        self.pmc_zip_folder = "pmc/zip/"
        self.archive_zip_bucket = (self.settings.publishing_buckets_prefix
                                   + self.settings.archive_bucket)

        # Local directory settings
        self.TMP_DIR = "tmp_dir"
        self.INPUT_DIR = "input_dir"
        self.ZIP_DIR = "zip_dir"
        self.FTP_TO_SOMEWHERE_DIR = "ftp_outbox"
        self.RENAME_DIR = "renamed_files"
        self.JUNK_DIR = "junk_dir"

        # Outgoing FTP settings are set later
        self.FTP_URI = None
        self.FTP_USERNAME = None
        self.FTP_PASSWORD = None
        self.FTP_CWD = None
        self.FTP_SUBDIR = []

        # SFTP settings
        self.SFTP_URI = None
        self.SFTP_USERNAME = None
        self.SFTP_PASSWORD = None
        self.SFTP_CWD = None

        # journal
        self.journal = 'elife'

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Data passed to this activity
        elife_id = data["data"]["elife_id"]
        workflow = data["data"]["workflow"]

        # Create output directories
        self.create_activity_directories()

        # Download the S3 objects
        self.download_files_from_s3(elife_id, workflow)

        # Set FTP settings
        self.set_ftp_settings(elife_id, workflow)

        # FTP to endpoint
        try:
            if workflow == 'HEFCE':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)

                #self.ftp_to_endpoint(zipfiles, self.FTP_SUBDIR, passive=True)
                # SFTP now
                sub_dir = "{:05d}".format(int(elife_id))
                self.sftp_to_endpoint(zipfiles, sub_dir)

            if workflow == 'Cengage':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)
                self.ftp_to_endpoint(zipfiles, passive=True)

            if workflow == 'Scopus':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)
                self.ftp_to_endpoint(zipfiles, passive=True)

            if workflow == 'WoS':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)
                self.ftp_to_endpoint(zipfiles, passive=True)

            if workflow == 'GoOA':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)
                self.ftp_to_endpoint(zipfiles, passive=True)

            if workflow == 'CNPIEC':
                file_type = "/*.zip"
                zipfiles = glob.glob(self.get_tmp_dir() + os.sep +
                                     self.FTP_TO_SOMEWHERE_DIR + file_type)
                self.ftp_to_endpoint(zipfiles, passive=True)

        except:
            # Something went wrong, fail
            if self.logger:
                self.logger.exception('exception in FTPArticle, data: %s' %
                                      json.dumps(data, sort_keys=True, indent=4))
            result = False
            self.clean_tmp_dir()
            return result

        # Return the activity result, True or False
        result = True
        self.clean_tmp_dir()
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
            self.FTP_CWD = self.settings.HEFCE_FTP_CWD
            # Subfolders to create when FTPing
            self.FTP_SUBDIR.append(str(doi_id).zfill(5))

            # SFTP settings

            self.SFTP_URI = self.settings.HEFCE_SFTP_URI
            self.SFTP_USERNAME = self.settings.HEFCE_SFTP_USERNAME
            self.SFTP_PASSWORD = self.settings.HEFCE_SFTP_PASSWORD
            self.SFTP_CWD = self.settings.HEFCE_SFTP_CWD

        if workflow == 'Cengage':
            self.FTP_URI = self.settings.CENGAGE_FTP_URI
            self.FTP_USERNAME = self.settings.CENGAGE_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.CENGAGE_FTP_PASSWORD
            self.FTP_CWD = self.settings.CENGAGE_FTP_CWD

        if workflow == 'Scopus':
            self.FTP_URI = self.settings.SCOPUS_FTP_URI
            self.FTP_USERNAME = self.settings.SCOPUS_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.SCOPUS_FTP_PASSWORD
            self.FTP_CWD = self.settings.SCOPUS_FTP_CWD

        if workflow == 'WoS':
            self.FTP_URI = self.settings.WOS_FTP_URI
            self.FTP_USERNAME = self.settings.WOS_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.WOS_FTP_PASSWORD
            self.FTP_CWD = self.settings.WOS_FTP_CWD

        if workflow == 'GoOA':
            self.FTP_URI = self.settings.GOOA_FTP_URI
            self.FTP_USERNAME = self.settings.GOOA_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.GOOA_FTP_PASSWORD
            self.FTP_CWD = self.settings.GOOA_FTP_CWD

        if workflow == 'CNPIEC':
            self.FTP_URI = self.settings.CNPIEC_FTP_URI
            self.FTP_USERNAME = self.settings.CNPIEC_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.CNPIEC_FTP_PASSWORD
            self.FTP_CWD = self.settings.CNPIEC_FTP_CWD

    def download_files_from_s3(self, doi_id, workflow):

        # Download PMC zip file if present
        pmc_zip_downloaded = self.download_pmc_zip_from_s3(doi_id, workflow)
        archive_zip_repackaged = None

        # if there is no PMC zip then download and convert the archive zip
        if not pmc_zip_downloaded:
            archive_zip_downloaded = self.download_archive_zip_from_s3(doi_id)
            if archive_zip_downloaded:
                archive_zip_repackaged = self.repackage_archive_zip_to_pmc_zip(doi_id)

        if pmc_zip_downloaded or archive_zip_repackaged:
            self.move_or_repackage_pmc_zip(doi_id, workflow)


    def download_archive_zip_from_s3(self, doi_id):
        "download the latest archive zip for the article to be repackaged"
        # Connect to S3 and bucket
        bucket_name = self.archive_zip_bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)
        s3_keys_in_bucket = s3lib.get_s3_keys_from_bucket(bucket=bucket)

        s3_keys = []
        for key in s3_keys_in_bucket:
            s3_keys.append({"name": key.name, "last_modified": key.last_modified})

        status = 'vor'
        s3_key_name = article_processing.latest_archive_zip_revision(
            doi_id, s3_keys, self.journal, status)

        if s3_key_name:
            # download it to disk
            s3_key = bucket.get_key(s3_key_name)
            filename = s3_key_name.split("/")[-1]
            filename_plus_path = os.path.join(self.get_tmp_dir(), self.TMP_DIR, filename)
            mode = "wb"
            with open(filename_plus_path, mode) as fp:
                s3_key.get_contents_to_file(fp)
            return True
        else:
            return False


    def repackage_archive_zip_to_pmc_zip(self, doi_id):
        "repackage the zip file in the TMP_DIR to a PMC zip format"
        # unzip contents
        zip_input_dir = os.path.join(self.get_tmp_dir(), self.TMP_DIR)
        zip_extracted_dir = os.path.join(self.get_tmp_dir(), self.JUNK_DIR)
        zip_renamed_files_dir = os.path.join(self.get_tmp_dir(), self.RENAME_DIR)
        pmc_zip_output_dir = os.path.join(self.get_tmp_dir(), self.INPUT_DIR)
        archive_zip_name = glob.glob(zip_input_dir + "/*.zip")[0]
        with zipfile.ZipFile(archive_zip_name, 'r') as myzip:
            myzip.extractall(zip_extracted_dir)
        # rename the files and profile the files
        file_name_map = article_processing.rename_files_remove_version_number(
            files_dir = zip_extracted_dir,
            output_dir = zip_renamed_files_dir
        )
        # convert the XML
        article_xml_file = glob.glob(zip_renamed_files_dir + "/*.xml")[0]
        article_processing.convert_xml(xml_file=article_xml_file,
                         file_name_map=file_name_map)
        # rezip the files into PMC zip format
        soup = parser.parse_document(article_xml_file)
        volume = parser.volume(soup)
        pmc_zip_file_name = article_processing.new_pmc_zip_filename(self.journal, volume, doi_id)
        with zipfile.ZipFile(os.path.join(pmc_zip_output_dir, pmc_zip_file_name), 'w',
                             zipfile.ZIP_DEFLATED, allowZip64=True) as new_zipfile:
            dirfiles = article_processing.file_list(zip_renamed_files_dir)
            for df in dirfiles:
                filename = df.split(os.sep)[-1]
                new_zipfile.write(df, filename)
        return True


    def download_pmc_zip_from_s3(self, doi_id, workflow):
        """
        Simple download of PMC zip file from the live bucket
        """
        bucket_name = self.pmc_zip_bucket
        prefix = self.pmc_zip_folder

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id,
                               self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=prefix)

        s3_key_name = s3lib.latest_pmc_zip_revision(doi_id, s3_key_names)

        if s3_key_name:

            # Download
            s3_key = bucket.get_key(s3_key_name)

            filename = s3_key_name.split("/")[-1]

            filename_plus_path = (self.get_tmp_dir() + os.sep +
                                  self.INPUT_DIR + os.sep + filename)
            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()

            return True
        else:
            return False


    def move_or_repackage_pmc_zip(self, doi_id, workflow):
        """
        Run if we downloaded a PMC zip file, either
        create a new zip for only the xml and pdf files, or
        move the entire zip to the ftp folder if we want to send the full article pacakge
        """

        # Repackage or move the zip depending on the workflow type
        if workflow == 'Cengage' or workflow == 'Scopus' or workflow == 'WoS':
            # Extract the zip and build a new zip
            file_type = "/*.zip"
            zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.INPUT_DIR + file_type)
            to_dir = self.get_tmp_dir() + os.sep + self.TMP_DIR
            for filename in zipfiles:
                myzip = zipfile.ZipFile(filename, 'r')
                myzip.extractall(to_dir)

            # Create the new zip
            zip_file_name = 'elife-' + str(doi_id).zfill(5) + '-xml-pdf.zip'
            zip_dir = self.get_tmp_dir() + os.sep + self.ZIP_DIR
            new_zipfile = zipfile.ZipFile(zip_dir + os.sep + zip_file_name, 'w',
                                          zipfile.ZIP_DEFLATED, allowZip64=True)
            # Add files
            ignore_name_fragments = ["-supp", "-data", "-code"]
            file_types = ["/*.pdf", "/*.xml"]
            for file_type in file_types:
                files = glob.glob(to_dir + file_type)
                for file in files:
                    # Ignore some files that are PDF we do not want to include
                    for ignore in ignore_name_fragments:
                        if ignore in file:
                            continue
                    filename = file.split(os.sep)[-1]
                    new_zipfile.write(file, filename)

            # Close zip
            new_zipfile.close()

            # Move the zip
            shutil.move(zip_dir + os.sep + zip_file_name, self.get_tmp_dir() + os.sep +
                        self.FTP_TO_SOMEWHERE_DIR + os.sep)

        else:
            # Default, move all the zip files from TMP_DIR to FTP_OUTBOX
            file_type = "/*.zip"
            zipfiles = glob.glob(self.get_tmp_dir() + os.sep + self.INPUT_DIR + file_type)
            for filename in zipfiles:
                shutil.move(filename, self.get_tmp_dir() + os.sep +
                            self.FTP_TO_SOMEWHERE_DIR + os.sep)

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

    def ftp_to_endpoint(self, uploadfiles, sub_dir_list=None, passive=True):
        for uploadfile in uploadfiles:
            ftp = FTP()
            if passive is False:
                ftp.set_pasv(False)
            ftp.connect(self.FTP_URI)
            ftp.login(self.FTP_USERNAME, self.FTP_PASSWORD)

            self.ftp_cwd_mkd(ftp, "/")
            if self.FTP_CWD != "":
                self.ftp_cwd_mkd(ftp, self.FTP_CWD)
            if sub_dir_list is not None:
                for sub_dir in sub_dir_list:
                    self.ftp_cwd_mkd(ftp, sub_dir)

            self.ftp_upload(ftp, uploadfile)
            ftp.quit()

    def sftp_to_endpoint(self, uploadfiles, sub_dir=None):
        """
        Using the sftp provider module, connect to sftp server and transmit files
        """
        sftp = sftplib.SFTP(logger=self.logger)
        sftp_client = sftp.sftp_connect(self.SFTP_URI, self.SFTP_USERNAME, self.SFTP_PASSWORD)

        if sftp_client is not None:
            sftp.sftp_to_endpoint(sftp_client, uploadfiles, self.SFTP_CWD, sub_dir)

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        try:
            os.mkdir(self.get_tmp_dir() + os.sep + self.TMP_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.INPUT_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.ZIP_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.FTP_TO_SOMEWHERE_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.RENAME_DIR)
            os.mkdir(self.get_tmp_dir() + os.sep + self.JUNK_DIR)
        except OSError:
            pass
