import os
import json
import zipfile
import glob
import shutil
import re
from elifetools import parseJATS as parser
from provider import article_processing, utils
from provider.storage_provider import storage_context
import provider.sftp as sftplib
from provider.ftp import FTP
from activity.objects import Activity


JOURNAL = "elife"
ZIP_FILE_PREFIX = "%s-" % JOURNAL


class activity_FTPArticle(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FTPArticle, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FTPArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download VOR files and publish by FTP to some particular place."
        )

        # Bucket settings
        self.archive_zip_bucket = (
            self.settings.publishing_buckets_prefix + self.settings.archive_bucket
        )

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
        self.FTP_SUBDIR_LIST = []

        # SFTP settings
        self.SFTP_URI = None
        self.SFTP_USERNAME = None
        self.SFTP_PASSWORD = None
        self.SFTP_CWD = None
        self.SFTP_SUBDIR = None

        # journal
        self.journal = JOURNAL

        self.workflow = None
        self.doi_id = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

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
        try:
            self.set_ftp_settings(elife_id, workflow)
        except:
            # Something went wrong, fail
            if self.logger:
                self.logger.exception(
                    "exception in FTPArticle when invoking set_ftp_settings(), data: %s"
                    % json.dumps(data, sort_keys=True, indent=4)
                )
            self.clean_tmp_dir()
            return False

        # FTP to endpoint
        try:
            zipfiles = glob.glob(
                self.directories.get("FTP_TO_SOMEWHERE_DIR") + "/*.zip"
            )
            if self.logger:
                self.logger.info(
                    "FTPArticle running %s workflow for article %s, attempting to send files: %s"
                    % (self.workflow, self.doi_id, zipfiles)
                )
            if workflow == "HEFCE":
                self.sftp_to_endpoint(zipfiles, self.SFTP_SUBDIR)
            if workflow == "Cengage":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "WoS":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "GoOA":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "CNPIEC":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "CNKI":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "CLOCKSS":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "OVID":
                self.ftp_to_endpoint(
                    zipfiles, sub_dir_list=self.FTP_SUBDIR_LIST, passive=True
                )
            if workflow == "Zendy":
                self.sftp_to_endpoint(zipfiles)
            if workflow == "OASwitchboard":
                # send XML files only, unzipped
                with zipfile.ZipFile(zipfiles[0], "r") as open_zip:
                    open_zip.extractall(self.directories.get("FTP_TO_SOMEWHERE_DIR"))
                uploadfiles = glob.glob(
                    self.directories.get("FTP_TO_SOMEWHERE_DIR") + "/*.xml"
                )
                self.sftp_to_endpoint(uploadfiles)

        except:
            # Something went wrong, fail
            if self.logger:
                self.logger.exception(
                    "exception in FTPArticle, data: %s"
                    % json.dumps(data, sort_keys=True, indent=4)
                )
            result = False
            self.clean_tmp_dir()
            return result

        # Return the activity result, True or False
        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, finished sending files: %s"
                % (self.workflow, self.doi_id, zipfiles)
            )
        result = True
        self.clean_tmp_dir()
        return result

    def set_ftp_settings(self, doi_id, workflow):
        """
        Set the outgoing FTP server settings based on the
        workflow type specified
        """
        # temporary transitional method to support using class properties as credentials
        credentials = collect_credentials(self.settings, doi_id, workflow)
        for key, value in credentials.items():
            setattr(self, key, value)

    def download_files_from_s3(self, doi_id, workflow):

        # download and convert the archive zip
        archive_zip_downloaded = self.download_archive_zip_from_s3(doi_id)
        if archive_zip_downloaded:
            archive_zip_repackaged = self.repackage_archive_zip_to_pmc_zip(doi_id)

        if archive_zip_repackaged:
            self.move_or_repackage_pmc_zip(doi_id, workflow)
        else:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, failed to package any zip files"
                % (workflow, doi_id)
            )

    def download_archive_zip_from_s3(self, doi_id):
        "download the latest archive zip for the article to be repackaged"
        # Connect to S3 and bucket
        bucket_name = self.archive_zip_bucket
        storage = storage_context(self.settings)
        bucket_resource = self.settings.storage_provider + "://" + bucket_name + "/"
        s3_keys_in_bucket = storage.list_resources(bucket_resource, return_keys=True)

        s3_keys = []
        for key in s3_keys_in_bucket:
            s3_keys.append(
                {
                    "name": key.get("Key"),
                    "last_modified": key.get("LastModified").strftime(
                        utils.DATE_TIME_FORMAT
                    ),
                }
            )

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
            filename = s3_key_name.rsplit("/", 1)[-1]
            filename_plus_path = os.path.join(self.directories.get("TMP_DIR"), filename)
            file_resource_origin = (
                self.settings.storage_provider + "://" + bucket_name + "/" + filename
            )
            with open(filename_plus_path, "wb") as open_file:
                storage.get_resource_to_file(file_resource_origin, open_file)
            if self.logger:
                self.logger.info(
                    "FTPArticle running %s workflow for article %s, downloaded archive zip %s"
                    % (self.workflow, self.doi_id, filename)
                )
            return True

        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, could not download an archive zip"
                % (self.workflow, self.doi_id)
            )
        return False

    def repackage_archive_zip_to_pmc_zip(self, doi_id):
        "repackage the zip file in the TMP_DIR to a PMC zip format"
        # unzip contents
        zip_input_dir = self.directories.get("TMP_DIR")
        zip_extracted_dir = self.directories.get("JUNK_DIR")
        zip_renamed_files_dir = self.directories.get("RENAME_DIR")
        pmc_zip_output_dir = self.directories.get("INPUT_DIR")
        archive_zip_name = glob.glob(zip_input_dir + "/*.zip")[0]
        with zipfile.ZipFile(archive_zip_name, "r") as myzip:
            myzip.extractall(zip_extracted_dir)
        # rename the files and profile the files
        file_name_map = article_processing.rename_files_remove_version_number(
            files_dir=zip_extracted_dir, output_dir=zip_renamed_files_dir
        )
        if self.logger:
            self.logger.info(
                "FTPArticle running %s workflow for article %s, file_name_map"
                % (self.workflow, self.doi_id)
            )
            self.logger.info(file_name_map)
        # convert the XML
        article_xml_file = glob.glob(zip_renamed_files_dir + "/*.xml")[0]
        article_processing.convert_xml(
            xml_file=article_xml_file, file_name_map=file_name_map
        )
        # rezip the files into PMC zip format
        soup = parser.parse_document(article_xml_file)
        volume = parser.volume(soup)
        pmc_zip_file_name = article_processing.new_pmc_zip_filename(
            self.journal, volume, doi_id
        )
        with zipfile.ZipFile(
            os.path.join(pmc_zip_output_dir, pmc_zip_file_name),
            "w",
            zipfile.ZIP_DEFLATED,
            allowZip64=True,
        ) as new_zipfile:
            dirfiles = article_processing.file_list(zip_renamed_files_dir)
            for dir_file in dirfiles:
                filename = dir_file.split(os.sep)[-1]
                new_zipfile.write(dir_file, filename)
        return True

    def move_or_repackage_pmc_zip(self, doi_id, workflow):
        """
        Run if we downloaded a PMC zip file, either
        create a new zip for only the xml and pdf files, or
        move the entire zip to the ftp folder if we want to send the full article pacakge
        """

        # Repackage or move the zip depending on the workflow type
        if workflow in ["Cengage", "WoS", "CNKI", "OASwitchboard"]:
            if workflow in ["CNKI", "OASwitchboard"]:
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
            with zipfile.ZipFile(filename, "r") as open_zip_file:
                open_zip_file.extractall(to_dir)

        # Create the new zip
        zip_file_path = os.path.join(
            self.directories.get("ZIP_DIR"),
            new_zip_file_name(
                doi_id, ZIP_FILE_PREFIX, zip_file_suffix(keep_file_types)
            ),
        )
        with zipfile.ZipFile(
            zip_file_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as new_zipfile:
            # Add files
            for file_type in file_type_matches(keep_file_types):
                files = glob.glob(to_dir + file_type)
                for to_dir_file in files:
                    add_file = True
                    # Ignore some files that are PDF we do not want to include
                    for ignore in ignore_name_fragments:
                        if ignore in to_dir_file:
                            add_file = False
                            break
                    if add_file:
                        filename = to_dir_file.split(os.sep)[-1]
                        new_zipfile.write(to_dir_file, filename)

        # Move the zip
        shutil.move(
            zip_file_path, self.directories.get("FTP_TO_SOMEWHERE_DIR") + os.sep
        )

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
                passive=passive,
            )
            self.logger.info("Connected to FTP server %s" % self.FTP_URI)
        except Exception as exception:
            self.logger.exception(
                "Exception connecting to FTP server %s: %s" % (self.FTP_URI, exception)
            )
            raise

        for uploadfile in uploadfiles:
            try:
                self.logger.info(
                    "Uploading file %s to FTP server %s" % (uploadfile, self.FTP_URI)
                )
                ftp_provider.ftp_cwd_mkd(ftp_instance, "/")
                if self.FTP_CWD != "":
                    ftp_provider.ftp_cwd_mkd(ftp_instance, self.FTP_CWD)
                if sub_dir_list is not None:
                    for sub_dir in sub_dir_list:
                        ftp_provider.ftp_cwd_mkd(ftp_instance, sub_dir)
                ftp_provider.ftp_upload(ftp_instance, uploadfile)
                self.logger.info(
                    "Completed uploading file %s to FTP server %s"
                    % (uploadfile, self.FTP_URI)
                )
            except Exception as exception:
                self.logger.exception(
                    "Exception in uploading file %s by FTP in %s: %s"
                    % (uploadfile, self.name, exception)
                )
                ftp_provider.ftp_disconnect(ftp_instance)
                raise

        try:
            # disconnect the FTP connection
            ftp_provider.ftp_disconnect(ftp_instance)
            self.logger.info("Disconnected from FTP server %s" % self.FTP_URI)
        except Exception as exception:
            self.logger.exception(
                "Exception disconnecting from FTP server %s: %s"
                % (self.FTP_URI, exception)
            )
            raise

    def sftp_to_endpoint(self, uploadfiles, sub_dir=None):
        """
        Using the sftp provider module, connect to sftp server and transmit files
        """
        sftp = sftplib.SFTP(logger=self.logger)
        sftp_client = sftp.sftp_connect(
            self.SFTP_URI, self.SFTP_USERNAME, self.SFTP_PASSWORD
        )

        if sftp_client is not None:
            sftp.sftp_to_endpoint(sftp_client, uploadfiles, self.SFTP_CWD, sub_dir)

        sftp.disconnect()


def zip_file_suffix(file_types):
    """suffix for new zip file name"""
    return "-%s.zip" % "-".join(file_types)


def new_zip_file_name(doi_id, prefix, suffix):
    return "%s%s%s" % (prefix, utils.pad_msid(doi_id), suffix)


def file_type_matches(file_types):
    """wildcard file name matches for the file types to include"""
    return ["/*.%s" % file_type for file_type in file_types]


def collect_credentials(settings, doi_id, workflow):
    "Set the FTP and SFTP server settings based on the workflow type and article doi_id"

    credentials = {}

    if workflow == "HEFCE":
        credentials["FTP_URI"] = settings.HEFCE_FTP_URI
        credentials["FTP_USERNAME"] = settings.HEFCE_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.HEFCE_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.HEFCE_FTP_CWD
        credentials["FTP_SUBDIR_LIST"] = [utils.pad_msid(doi_id)]

        # SFTP settings
        credentials["SFTP_URI"] = settings.HEFCE_SFTP_URI
        credentials["SFTP_USERNAME"] = settings.HEFCE_SFTP_USERNAME
        credentials["SFTP_PASSWORD"] = settings.HEFCE_SFTP_PASSWORD
        credentials["SFTP_CWD"] = settings.HEFCE_SFTP_CWD
        credentials["SFTP_SUBDIR"] = utils.pad_msid(doi_id)

    if workflow == "Cengage":
        credentials["FTP_URI"] = settings.CENGAGE_FTP_URI
        credentials["FTP_USERNAME"] = settings.CENGAGE_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.CENGAGE_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.CENGAGE_FTP_CWD

    if workflow == "WoS":
        credentials["FTP_URI"] = settings.WOS_FTP_URI
        credentials["FTP_USERNAME"] = settings.WOS_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.WOS_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.WOS_FTP_CWD

    if workflow == "GoOA":
        credentials["FTP_URI"] = settings.GOOA_FTP_URI
        credentials["FTP_USERNAME"] = settings.GOOA_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.GOOA_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.GOOA_FTP_CWD

    if workflow == "CNPIEC":
        credentials["FTP_URI"] = settings.CNPIEC_FTP_URI
        credentials["FTP_USERNAME"] = settings.CNPIEC_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.CNPIEC_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.CNPIEC_FTP_CWD

    if workflow == "CNKI":
        credentials["FTP_URI"] = settings.CNKI_FTP_URI
        credentials["FTP_USERNAME"] = settings.CNKI_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.CNKI_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.CNKI_FTP_CWD

    if workflow == "CLOCKSS":
        credentials["FTP_URI"] = settings.CLOCKSS_FTP_URI
        credentials["FTP_USERNAME"] = settings.CLOCKSS_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.CLOCKSS_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.CLOCKSS_FTP_CWD

    if workflow == "OVID":
        credentials["FTP_URI"] = settings.OVID_FTP_URI
        credentials["FTP_USERNAME"] = settings.OVID_FTP_USERNAME
        credentials["FTP_PASSWORD"] = settings.OVID_FTP_PASSWORD
        credentials["FTP_CWD"] = settings.OVID_FTP_CWD

    if workflow == "Zendy":
        credentials["SFTP_URI"] = settings.ZENDY_SFTP_URI
        credentials["SFTP_USERNAME"] = settings.ZENDY_SFTP_USERNAME
        credentials["SFTP_PASSWORD"] = settings.ZENDY_SFTP_PASSWORD
        credentials["SFTP_CWD"] = settings.ZENDY_SFTP_CWD

    if workflow == "OASwitchboard":
        credentials["SFTP_URI"] = settings.OASWITCHBOARD_SFTP_URI
        credentials["SFTP_USERNAME"] = settings.OASWITCHBOARD_SFTP_USERNAME
        credentials["SFTP_PASSWORD"] = settings.OASWITCHBOARD_SFTP_PASSWORD
        credentials["SFTP_CWD"] = settings.OASWITCHBOARD_SFTP_CWD

    return credentials
