import os
import time
import json
import zipfile
import re
import glob
from elifetools import xmlio
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
        xml_search_folders = [
            self.directories.get("TMP_DIR"),
            self.directories.get("OUTPUT_DIR"),
        ]

        fid, volume = profile_article(article_xml_file(xml_search_folders))

        # Rename the files
        file_name_map = article_processing.rename_files_remove_version_number(
            self.directories.get("TMP_DIR"),
            self.directories.get("OUTPUT_DIR"),
            self.logger,
        )

        (
            verified,
            renamed_list,
            not_renamed_list,
        ) = article_processing.verify_rename_files(file_name_map)

        self.logger.info(
            "verified %s: %s" % (self.directories.get("INPUT_DIR"), verified)
        )
        self.logger.info("file_name_map: %s" % file_name_map)
        if renamed_list:
            self.logger.info("renamed: %s" % renamed_list)
        if not_renamed_list:
            self.logger.info("not renamed: %s" % not_renamed_list)

        # Temporary XML rewrite of related-object tag
        alter_xml(article_xml_file(xml_search_folders), self.logger)

        # Convert the XML
        article_processing.convert_xml(
            article_xml_file(xml_search_folders), file_name_map
        )

        # Get the new zip file name
        # take into account the r1 r2 revision numbers when replacing an article
        revision = self.zip_revision_number(fid)
        self.zip_file_name = new_zip_filename(journal, volume, fid, revision)
        self.logger.info("new PMC zip file name: " + str(self.zip_file_name))
        zip_file_path = self.directories.get("ZIP_DIR") + os.sep + self.zip_file_name
        create_new_zip(zip_file_path, self.directories.get("OUTPUT_DIR"), self.logger)

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
        if verified and self.zip_file_name and not article_retracted_status:
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
            result = bool(verified and ftp_status)

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


def create_new_zip(zip_file_name, files_dir, logger):

    logger.info("creating new PMC zip file named " + zip_file_name)

    with zipfile.ZipFile(
        zip_file_name, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as new_zipfile:
        dirfiles = article_processing.file_list(files_dir)
        for article_file_name in dirfiles:
            filename = article_file_name.split(os.sep)[-1]
            new_zipfile.write(article_file_name, filename)


def get_journal(document):
    """get the journal name from the input zip file"""
    if document:
        info = ArticleInfo(article_processing.file_name_from_name(document))
        return info.journal
    return None


def article_xml_file(folders):
    """
    Directories the XML file might be in depending on the step
    """
    for folder_name in folders:
        for file_name in article_processing.file_list(folder_name):
            info = ArticleInfo(article_processing.file_name_from_name(file_name))
            if info.file_type == "ArticleXML":
                return file_name
    return None


def new_zip_filename(journal, volume, fid, revision=None):

    filename = journal
    filename = filename + "-" + str(volume).zfill(2)
    filename = filename + "-" + str(fid).zfill(5)
    if revision:
        filename = filename + ".r" + str(revision)
    filename += ".zip"
    return filename


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
    return u"Exception raised sending article to PMC: {document}".format(
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


def alter_xml(xml_file, logger):
    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    # Convert related-object tag
    for xml_tag in root.findall("./sub-article/front-stub/related-object"):
        logger.info("Converting related-object tag to ext-link tag in sub-article")
        xml_tag.tag = "ext-link"
        xml_tag.set("ext-link-type", "uri")
        # delete attributes
        for attribute_name in ["link-type", "object-id", "object-id-type"]:
            if xml_tag.attrib.get(attribute_name):
                del xml_tag.attrib[attribute_name]

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    f = open(xml_file, "wb")
    f.write(reparsed_string)
    f.close()
