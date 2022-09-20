import os
import time
import json
import zipfile
import re
import glob
from elifetools import parseJATS as parser
import provider.s3lib as s3lib
from provider.article_structure import ArticleInfo
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, email_provider, lax_provider, utils
from provider.ftp import FTP
from activity.objects import Activity


class activity_PMCDeposit(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PMCDeposit, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "PMCDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download single zip file an article, repackage it, "
            + "send to PMC and notify them."
        )

        # Local directory settings
        self.directories = {
            "TMP_DIR": self.get_tmp_dir() + os.sep + "tmp_dir",
            "INPUT_DIR": self.get_tmp_dir() + os.sep + "input_dir",
            "ZIP_DIR": self.get_tmp_dir() + os.sep + "zip_dir",
            "OUTPUT_DIR": self.get_tmp_dir() + os.sep + "output_dir",
            "JUNK_DIR": os.path.join(self.get_tmp_dir(), "junk_dir"),
        }

        # Bucket settings
        self.input_bucket = settings.publishing_buckets_prefix + settings.archive_bucket

        self.publish_bucket = settings.poa_packaging_bucket
        self.published_folder = "pmc/published"
        self.published_zip_folder = "pmc/zip"

        self.document = None
        self.zip_file_name = None

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        run = data["run"]
        session = get_session(self.settings, data, run)

        # Data passed to this activity
        self.document = data["data"]["document"]

        # Create output directories
        self.make_activity_directories(list(self.directories.values()))

        # Check the settings for suitability to send
        if not self.settings.PMC_FTP_URI:
            self.logger.info(
                "%s settings PMC_FTP_URI value is blank, cannot send files", self.name
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # Download the S3 objects
        download_status = self.download_files_from_s3(self.document)

        if not download_status:
            self.logger.info(
                "failed to download zip in PMCDeposit: " + str(self.document)
            )
            # Clean up disk
            self.clean_tmp_dir()
            # Retry activity again
            return self.ACTIVITY_TEMPORARY_FAILURE

        # Unzip the input zip file contents
        input_zip_file_name = os.path.join(
            self.directories.get("INPUT_DIR"), self.document
        )
        unzip_article_files(
            input_zip_file_name, self.directories.get("TMP_DIR"), self.logger
        )

        # Profile the article
        journal = get_journal(self.document)
        article_xml_file = article_processing.unzip_article_xml(
            input_zip_file_name, self.directories.get("JUNK_DIR")
        )
        fid, volume = profile_article(article_xml_file)
        # Get the new zip file name
        # take into account the r1 r2 revision numbers when replacing an article
        revision = self.zip_revision_number(fid)
        self.zip_file_name = article_processing.new_pmc_zip_filename(
            journal, volume, fid, revision
        )
        self.logger.info("new PMC zip file name: " + str(self.zip_file_name))
        zip_file_path = os.path.join(
            self.directories.get("ZIP_DIR"), self.zip_file_name
        )

        # repackage the archive zip into PMC zip format
        archive_zip_repackaged = article_processing.repackage_archive_zip_to_pmc_zip(
            input_zip_file_name,
            zip_file_path,
            self.directories.get("TMP_DIR"),
            self.logger,
            alter_xml=True,
        )

        # check if the article is retracted
        article_retracted_status = lax_provider.article_retracted_status(
            fid, self.settings
        )
        self.logger.info(
            "%s article_id %s article_retracted_status: %s"
            % (self.name, fid, article_retracted_status)
        )
        if article_retracted_status is None:
            self.logger.info(
                "%s could not determine article retracted status for article id %s"
                % (self.name, fid)
            )
            # Clean up disk
            self.clean_tmp_dir()
            return self.ACTIVITY_TEMPORARY_FAILURE

        # FTP the zip
        ftp_status = None
        if (
            archive_zip_repackaged
            and self.zip_file_name
            and not article_retracted_status
        ):
            try:
                ftp_status = self.ftp_to_endpoint(self.directories.get("ZIP_DIR"))
            except Exception as exception:
                message = "Exception in ftp_to_endpoint sending file %s: %s" % (
                    self.zip_file_name,
                    exception,
                )
                self.logger.exception(message)
                # send email once when an exception is raised
                if not session.get_value("ftp_exception"):
                    subject = ftp_exception_email_subject(self.document)
                    send_ftp_exception_email(
                        subject, message, self.settings, self.logger
                    )
                    session.store_value("ftp_exception", 1)
                # Clean up disk
                self.clean_tmp_dir()
                # return a temporary failure
                return self.ACTIVITY_TEMPORARY_FAILURE

        if ftp_status is True or article_retracted_status is True:
            self.upload_article_zip_to_s3()

        # Return the activity result, True or False
        if article_retracted_status:
            result = True
        else:
            result = bool(archive_zip_repackaged and ftp_status)

        # Clean up disk
        self.clean_tmp_dir()

        return result

    def ftp_to_endpoint(self, from_dir, file_type="/*.zip", passive=True):
        """
        FTP files to endpoint
        as specified by the file_type to use in the glob
        e.g. "/*.zip"
        """
        try:
            ftp_provider = FTP(self.logger)
            ftp_instance = ftp_provider.ftp_connect(
                uri=self.settings.PMC_FTP_URI,
                username=self.settings.PMC_FTP_USERNAME,
                password=self.settings.PMC_FTP_PASSWORD,
                passive=passive,
            )
        except Exception as exception:
            self.logger.exception("Exception connecting to FTP server: %s" % exception)
            raise

        # collect the list of files
        zipfiles = glob.glob(from_dir + file_type)

        try:
            # transfer them by FTP to the endpoint
            ftp_provider.ftp_to_endpoint(
                ftp_instance=ftp_instance,
                uploadfiles=zipfiles,
                sub_dir_list=[self.settings.PMC_FTP_CWD],
            )
        except Exception as exception:
            self.logger.exception(
                "Exception in transfer of files by FTP: %s" % exception
            )
            ftp_provider.ftp_disconnect(ftp_instance)
            raise

        try:
            # disconnect the FTP connection
            ftp_provider.ftp_disconnect(ftp_instance)
        except Exception as exception:
            self.logger.exception(
                "Exception disconnecting from FTP server: %s" % exception
            )
            raise

        return True

    def download_files_from_s3(self, document):
        """download input zip document from the bucket"""
        self.logger.info("downloading VoR file " + document)
        bucket_name = self.input_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name

        file_name = document.split("/")[-1]
        file_path = os.path.join(self.directories.get("INPUT_DIR"), file_name)
        storage_resource_origin = orig_resource + "/" + document
        try:
            with open(file_path, "wb") as open_file:
                self.logger.info(
                    "Downloading %s to %s", (storage_resource_origin, file_path)
                )
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except IOError:
            self.logger.exception("Failed to download file %s.", document)
            return False
        return True

    def upload_article_zip_to_s3(self):
        """
        Upload PMC zip file to S3
        """
        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"

        for file_name in article_processing.file_list(self.directories.get("ZIP_DIR")):
            resource_dest = (
                storage_provider
                + bucket_name
                + "/"
                + self.published_zip_folder
                + "/"
                + article_processing.file_name_from_name(file_name)
            )
            storage.set_resource_from_filename(resource_dest, file_name)

    def zip_revision_number(self, fid):
        """
        Look at previously supplied files and determine the
        next revision number
        """
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = (
            storage_provider + self.publish_bucket + "/" + self.published_zip_folder
        )

        s3_key_names = storage.list_resources(orig_resource)
        # remove the subfolder name from file names
        s3_key_names = [filename.rsplit("/", 1)[-1] for filename in s3_key_names]
        return next_revision_number(fid, s3_key_names)


def next_revision_number(fid, s3_key_names):
    """Given article id and existing zip file names return the next revision number"""
    revision = None
    s3_key_name = s3lib.latest_pmc_zip_revision(fid, s3_key_names)

    if s3_key_name:
        # Found an existing PMC zip file, look for a revision number
        revision_match = re.match(r".*r(.*)\.zip$", s3_key_name)
        if revision_match is None:
            # There is a zip but no revision number, use 1
            revision = 1
        else:
            # Use the latest revision plus 1
            revision = int(revision_match.group(1)) + 1
    return revision


def unzip_article_files(zip_file_name, to_dir, logger):
    """If file extension is zip, then unzip contents"""
    if article_processing.file_extension(zip_file_name) == "zip":
        # Unzip
        logger.info("going to unzip " + zip_file_name + " to " + to_dir)
        with zipfile.ZipFile(zip_file_name, "r") as open_file:
            open_file.extractall(to_dir)


def get_journal(document):
    """get the journal name from the input zip file"""
    if document:
        info = ArticleInfo(article_processing.file_name_from_name(document))
        return info.journal
    return None


def profile_article(document):
    """
    Temporary, profile the article by folder names in test data set
    In real code we still want this to return the same values
    """
    soup = parser.parse_document(document)

    # elife id / doi id / manuscript id
    fid = parser.doi(soup).split(".")[-1]

    # volume
    volume = parser.volume(soup)

    return fid, volume


def ftp_exception_email_subject(document):
    "email subject for sending an email"
    return "Exception raised sending article to PMC: {document}".format(
        document=document
    )


def send_ftp_exception_email(subject, message, settings, logger):
    "email error message to the recipients"

    datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
    body = email_provider.simple_email_body(datetime_string, message)
    sender_email = settings.ftp_deposit_error_sender_email

    recipient_email_list = email_provider.list_email_recipients(
        settings.ftp_deposit_error_recipient_email
    )

    messages = email_provider.simple_messages(
        sender_email, recipient_email_list, subject, body, logger=logger
    )
    logger.info("Formatted %d email error messages" % len(messages))

    details = email_provider.smtp_send_messages(settings, messages, logger)
    logger.info("Email sending details: %s" % str(details))
