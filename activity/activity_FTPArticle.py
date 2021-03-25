import os
import json
import zipfile
import glob
import shutil
import re

from elifetools import parseJATS as parser

from boto.s3.connection import S3Connection

from provider import article_processing, s3lib
import provider.sftp as sftplib
from provider.ftp import FTP
from activity.objects import Activity


JOURNAL = 'elife'
ZIP_FILE_PREFIX = '%s-' % JOURNAL


class activity_FTPArticle(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_FTPArticle, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "FTPArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = "Download VOR files and publish by FTP to some particular place."

        # Bucket settings
        self.pmc_zip_bucket = settings.poa_packaging_bucket
        self.pmc_zip_folder = "pmc/zip/"
        self.archive_zip_bucket = (self.settings.publishing_buckets_prefix
                                   + self.settings.archive_bucket)

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "ZIP_DIR": os.path.join(self.get_tmp_dir(), "zip_dir"),
            "FTP_TO_SOMEWHERE_DIR": os.path.join(self.get_tmp_dir(), "ftp_outbox"),
            "RENAME_DIR": os.path.join(self.get_tmp_dir(), "renamed_files"),
            "JUNK_DIR": os.path.join(self.get_tmp_dir(), "junk_dir"),
        }

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
        self.journal = JOURNAL

        self.workflow = None
        self.doi_id = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Data passed to this activity
        elife_id = data["data"]["elife_id"]
        workflow = data["data"]["workflow"]

        # Set some variables to use in logging
        self.workflow = workflow
        self.doi_id = elife_id

        # Create output directories
        self.make_activity_directories()

        # Download the S3 objects
        self.download_files_from_s3(elife_id, workflow)

        # Set FTP settings
        self.set_ftp_settings(elife_id, workflow)

        # FTP to endpoint
        try:
            zipfiles = glob.glob(self.directories.get("FTP_TO_SOMEWHERE_DIR") + "/*.zip")
            if self.logger:
                self.logger.info(
                    "FTPArticle running %s workflow for article %s, attempting to send files: %s"
                    % (self.workflow, self.doi_id, zipfiles))
            if workflow == 'HEFCE':
                # self.ftp_to_endpoint(zipfiles, self.FTP_SUBDIR, passive=True)
                # SFTP now
                sub_dir = "{:05d}".format(int(elife_id))
                self.sftp_to_endpoint(zipfiles, sub_dir)
            if workflow == 'Cengage':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'Scopus':
                self.sftp_to_endpoint(zipfiles)
            if workflow == 'WoS':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'GoOA':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'CNPIEC':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'CNKI':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'CLOCKSS':
                self.ftp_to_endpoint(zipfiles, passive=True)
            if workflow == 'OVID':
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
        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, finished sending files: %s"
                % (self.workflow, self.doi_id, zipfiles))
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

            # SFTP settings
            self.SFTP_URI = self.settings.SCOPUS_SFTP_URI
            self.SFTP_USERNAME = self.settings.SCOPUS_SFTP_USERNAME
            self.SFTP_PASSWORD = self.settings.SCOPUS_SFTP_PASSWORD
            self.SFTP_CWD = self.settings.SCOPUS_SFTP_CWD

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

        if workflow == 'CNKI':
            self.FTP_URI = self.settings.CNKI_FTP_URI
            self.FTP_USERNAME = self.settings.CNKI_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.CNKI_FTP_PASSWORD
            self.FTP_CWD = self.settings.CNKI_FTP_CWD

        if workflow == 'CLOCKSS':
            self.FTP_URI = self.settings.CLOCKSS_FTP_URI
            self.FTP_USERNAME = self.settings.CLOCKSS_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.CLOCKSS_FTP_PASSWORD
            self.FTP_CWD = self.settings.CLOCKSS_FTP_CWD

        if workflow == 'OVID':
            self.FTP_URI = self.settings.OVID_FTP_URI
            self.FTP_USERNAME = self.settings.OVID_FTP_USERNAME
            self.FTP_PASSWORD = self.settings.OVID_FTP_PASSWORD
            self.FTP_CWD = self.settings.OVID_FTP_CWD

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
        else:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, failed to package any zip files"
                % (self.workflow, self.doi_id))

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

        for status in ["vor", "poa"]:
            s3_key_name = article_processing.latest_archive_zip_revision(
                doi_id, s3_keys, self.journal, status
            )
            if s3_key_name:
                if self.logger:
                    self.logger.info(
                        "Latest archive zip for status %s, doi id %s, is s3 key name %s"
                        % (status, doi_id, s3_key_name)
                    )
                break
            else:
                if self.logger:
                    self.logger.info(
                        "For archive zip for status %s, doi id %s, no s3 key name was found"
                        % (status, doi_id)
                    )

        if s3_key_name:
            # download it to disk
            s3_key = bucket.get_key(s3_key_name)
            filename = s3_key_name.split("/")[-1]
            filename_plus_path = os.path.join(self.directories.get("TMP_DIR"), filename)
            mode = "wb"
            with open(filename_plus_path, mode) as open_file:
                s3_key.get_contents_to_file(open_file)
            if self.logger:
                self.logger.info(
                    "FTPArticle running %s workflow for article %s, downloaded archive zip %s"
                    % (self.workflow, self.doi_id, filename))
            return True

        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, could not download an archive zip"
                % (self.workflow, self.doi_id))
        return False

    def repackage_archive_zip_to_pmc_zip(self, doi_id):
        "repackage the zip file in the TMP_DIR to a PMC zip format"
        # unzip contents
        zip_input_dir = self.directories.get("TMP_DIR")
        zip_extracted_dir = self.directories.get("JUNK_DIR")
        zip_renamed_files_dir = self.directories.get("RENAME_DIR")
        pmc_zip_output_dir = self.directories.get("INPUT_DIR")
        archive_zip_name = glob.glob(zip_input_dir + "/*.zip")[0]
        with zipfile.ZipFile(archive_zip_name, 'r') as myzip:
            myzip.extractall(zip_extracted_dir)
        # rename the files and profile the files
        file_name_map = article_processing.rename_files_remove_version_number(
            files_dir=zip_extracted_dir,
            output_dir=zip_renamed_files_dir
        )
        if self.logger:
            self.logger.info("FTPArticle running %s workflow for article %s, file_name_map"
                             % (self.workflow, self.doi_id))
            self.logger.info(file_name_map)
        # convert the XML
        article_xml_file = glob.glob(zip_renamed_files_dir + "/*.xml")[0]
        article_processing.convert_xml(
            xml_file=article_xml_file,
            file_name_map=file_name_map)
        # rezip the files into PMC zip format
        soup = parser.parse_document(article_xml_file)
        volume = parser.volume(soup)
        pmc_zip_file_name = article_processing.new_pmc_zip_filename(self.journal, volume, doi_id)
        with zipfile.ZipFile(os.path.join(pmc_zip_output_dir, pmc_zip_file_name), 'w',
                             zipfile.ZIP_DEFLATED, allowZip64=True) as new_zipfile:
            dirfiles = article_processing.file_list(zip_renamed_files_dir)
            for dir_file in dirfiles:
                filename = dir_file.split(os.sep)[-1]
                new_zipfile.write(dir_file, filename)
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

            filename_plus_path = os.path.join(self.directories.get("INPUT_DIR"), filename)

            with open(filename_plus_path, "wb") as open_file:
                s3_key.get_contents_to_file(open_file)

            if self.logger:
                self.logger.info(
                    "FTPArticle running %s workflow for article %s, downloaded PMC zip %s"
                    % (workflow, doi_id, filename))
            return True

        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, could not download a PMC zip"
                % (workflow, doi_id))
        return False

    def move_or_repackage_pmc_zip(self, doi_id, workflow):
        """
        Run if we downloaded a PMC zip file, either
        create a new zip for only the xml and pdf files, or
        move the entire zip to the ftp folder if we want to send the full article pacakge
        """

        # Repackage or move the zip depending on the workflow type
        if workflow in ['Cengage', 'Scopus', 'WoS', 'CNKI']:
            if workflow == 'CNKI':
                file_types = ["xml"]
            else:
                file_types = ["xml", "pdf"]
            self.repackage_pmc_zip(doi_id, file_types)
        else:
            self.move_pmc_zip()

    def repackage_pmc_zip(self, doi_id, keep_file_types):
        """repackage the zip file to include only certain file types then move it to folder"""

        ignore_name_fragments = ["-supp", "-data", "-code"]

        # Extract the zip and build a new zip
        zipfiles = glob.glob(self.directories.get("INPUT_DIR") + "/*.zip")
        to_dir = self.directories.get("TMP_DIR")
        for filename in zipfiles:
            with zipfile.ZipFile(filename, 'r') as open_zip_file:
                open_zip_file.extractall(to_dir)

        # Create the new zip
        zip_file_path = os.path.join(
            self.directories.get("ZIP_DIR"),
            new_zip_file_name(doi_id, ZIP_FILE_PREFIX, zip_file_suffix(keep_file_types)))
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED,
                             allowZip64=True) as new_zipfile:
            # Add files
            for file_type in file_type_matches(keep_file_types):
                files = glob.glob(to_dir + file_type)
                for to_dir_file in files:
                    # Ignore some files that are PDF we do not want to include
                    for ignore in ignore_name_fragments:
                        if ignore in to_dir_file:
                            continue
                    filename = to_dir_file.split(os.sep)[-1]
                    new_zipfile.write(to_dir_file, filename)

        # Move the zip
        shutil.move(
            zip_file_path,
            self.directories.get("FTP_TO_SOMEWHERE_DIR") + os.sep)

    def move_pmc_zip(self):
        """Default, move all the zip files from TMP_DIR to FTP_OUTBOX"""
        zipfiles = glob.glob(self.directories.get("INPUT_DIR") + "/*.zip")
        for filename in zipfiles:
            # remove r revision number from the PMC zip file name
            new_filename = re.sub(r"\.r[0-9]*\.", ".", filename.split(os.sep)[-1])
            shutil.move(
                filename,
                os.path.join(
                    self.directories.get("FTP_TO_SOMEWHERE_DIR"), new_filename
                ),
            )

    def ftp_to_endpoint(self, uploadfiles, sub_dir_list=None, passive=True):
        "FTP files to endpoint"
        try:
            ftp_provider = FTP(self.logger)
            ftp_instance = ftp_provider.ftp_connect(
                uri=self.FTP_URI,
                username=self.FTP_USERNAME,
                password=self.FTP_PASSWORD,
                passive=passive
            )
            self.logger.info("Connected to FTP server %s" % self.FTP_URI)
        except Exception as exception:
            self.logger.exception(
                "Exception connecting to FTP server %s: %s" % (self.FTP_URI, exception))
            raise

        for uploadfile in uploadfiles:
            try:
                self.logger.info(
                    "Uploading file %s to FTP server %s" % (uploadfile, self.FTP_URI))
                ftp_provider.ftp_cwd_mkd(ftp_instance, "/")
                if self.FTP_CWD != "":
                    ftp_provider.ftp_cwd_mkd(ftp_instance, self.FTP_CWD)
                if sub_dir_list is not None:
                    for sub_dir in sub_dir_list:
                        ftp_provider.ftp_cwd_mkd(ftp_instance, sub_dir)
                ftp_provider.ftp_upload(ftp_instance, uploadfile)
                self.logger.info(
                    "Completed uploading file %s to FTP server %s" % (uploadfile, self.FTP_URI))
            except Exception as exception:
                self.logger.exception(
                    "Exception in uploading file %s by FTP in %s: %s" %
                    (uploadfile, self.name, exception))
                ftp_provider.ftp_disconnect(ftp_instance)
                raise

        try:
            # disconnect the FTP connection
            ftp_provider.ftp_disconnect(ftp_instance)
            self.logger.info("Disconnected from FTP server %s" % self.FTP_URI)
        except Exception as exception:
            self.logger.exception(
                "Exception disconnecting from FTP server %s: %s" % (self.FTP_URI, exception))
            raise

    def sftp_to_endpoint(self, uploadfiles, sub_dir=None):
        """
        Using the sftp provider module, connect to sftp server and transmit files
        """
        sftp = sftplib.SFTP(logger=self.logger)
        sftp_client = sftp.sftp_connect(self.SFTP_URI, self.SFTP_USERNAME, self.SFTP_PASSWORD)

        if sftp_client is not None:
            sftp.sftp_to_endpoint(sftp_client, uploadfiles, self.SFTP_CWD, sub_dir)


def zip_file_suffix(file_types):
    """suffix for new zip file name"""
    return '-%s.zip' % '-'.join(file_types)


def new_zip_file_name(doi_id, prefix, suffix):
    return '%s%s%s' % (prefix, str(doi_id).zfill(5), suffix)


def file_type_matches(file_types):
    """wildcard file name matches for the file types to include"""
    return ['/*.%s' % file_type for file_type in file_types]
