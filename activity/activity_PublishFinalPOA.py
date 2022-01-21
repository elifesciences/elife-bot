import os
import json
import time
import zipfile
import glob
import shutil
import re
from xml.etree.ElementTree import Element, SubElement
from elifetools import parseJATS as parser
from elifetools import xmlio
from provider.storage_provider import storage_context
from provider import email_provider, lax_provider, outbox_provider, utils
from activity.objects import Activity

"""
PublishFinalPOA activity
"""


class activity_PublishFinalPOA(Activity):
    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_PublishFinalPOA, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "PublishFinalPOA"
        self.version = "1"
        self.default_task_heartbeat_timeout = 60 * 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download POA files from a bucket, zip each article separately, "
            + "and upload to final bucket."
        )

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
            "JUNK_DIR": os.path.join(self.get_tmp_dir(), "junk_dir"),
            "DONE_DIR": os.path.join(self.get_tmp_dir(), "done_dir"),
        }

        # Bucket for outgoing files
        self.input_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "outbox/"
        self.published_folder_prefix = "published/"
        self.published_folder_name = None

        self.publish_bucket = (
            settings.publishing_buckets_prefix + settings.production_bucket
        )

        # Track the success of some steps
        self.activity_status = None
        self.approve_status = None
        self.publish_status = None

        # More file status tracking for reporting in email
        self.done_xml_files = []
        self.clean_from_outbox_files = []
        self.outbox_s3_key_names = []
        self.malformed_ds_file_names = []
        self.empty_ds_file_names = []
        self.unmatched_ds_file_names = []

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        # Download the S3 objects
        outbox_s3_key_names = outbox_provider.get_outbox_s3_key_names(
            self.settings, self.input_bucket, self.outbox_folder, xml_only=False
        )
        file_extensions = [
            ".xml",
            ".pdf",
            ".zip",
        ]
        self.outbox_s3_key_names = [
            s3_key
            for s3_key in outbox_s3_key_names
            if ".%s" % s3_key.split(".")[-1] in file_extensions
        ]
        self.logger.info(
            "PublishFinalPOA downloading files from S3 bucket: %s"
            % self.outbox_s3_key_names
        )
        outbox_provider.download_files_from_s3_outbox(
            self.settings,
            self.input_bucket,
            self.outbox_s3_key_names,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )

        # Approve files for publishing
        self.approve_status = self.approve_for_publishing()

        self.filter_ds_zip_files()
        self.filter_file_pairs()

        article_filenames_map = profile_article_files(self.directories.get("INPUT_DIR"))

        for doi_id, filenames in list(article_filenames_map.items()):

            article_xml_file_name = article_xml_from_filename_map(filenames)

            new_filenames = create_new_filenames(doi_id, filenames)

            if article_xml_file_name:
                xml_file = os.path.join(
                    self.directories.get("INPUT_DIR"), article_xml_file_name
                )
                modify_success = modify_xml(
                    xml_file, doi_id, new_filenames, self.settings, self.logger
                )
                if not modify_success:
                    continue

            revision = self.next_revision_number(doi_id)
            zip_file_name = new_zip_file_name(doi_id, revision)
            if revision and zip_file_name:
                self.zip_article_files(filenames, new_filenames, zip_file_name)
                # Add files to the lists to be processed after
                new_article_xml_file_name = article_xml_from_filename_map(new_filenames)
                self.done_xml_files.append(new_article_xml_file_name)
                self.clean_from_outbox_files = self.clean_from_outbox_files + filenames

        if self.approve_status is True:
            # Upload the zip files to the publishing bucket
            self.publish_status = self.upload_files_to_s3()

        # Set the published folder name as todays date
        date_stamp = utils.set_datestamp()
        self.published_folder_name = outbox_provider.get_to_folder_name(
            self.published_folder_prefix, date_stamp
        )

        # Clean the outbox
        if self.clean_from_outbox_files:
            outbox_provider.clean_outbox(
                self.settings,
                self.input_bucket,
                self.outbox_folder,
                self.published_folder_name,
                self.clean_from_outbox_files,
            )

        # Set the activity status of this activity based on successes
        if self.publish_status is not False:
            self.activity_status = True
        else:
            self.activity_status = False

        # Send email
        self.send_email()

        # Return the activity result, True or False
        result = True

        if self.activity_status is True:
            self.clean_tmp_dir()

        return result

    def next_revision_number(self, doi_id, status="poa"):
        """
        From the bucket, get a list of zip files
        and determine the next revision number to use
        """
        next_revision_number = 1

        bucket_name = self.publish_bucket

        file_extensions = []
        file_extensions.append(".zip")

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/"

        s3_key_names = storage.list_resources(orig_resource)

        max_revision_number = 0
        for key_name in s3_key_names:

            name_prefix = "elife-%s-%s-r" % (utils.pad_msid(doi_id), status)
            if key_name.startswith(name_prefix):
                # Attempt to get a revision number from the matching files
                try:
                    part = key_name.replace(name_prefix, "")
                    revision = int(part.split(".")[0])
                except (IndexError, ValueError):
                    revision = None
                if revision and revision > max_revision_number:
                    max_revision_number = revision

        if max_revision_number > 0:
            next_revision_number = max_revision_number + 1

        return next_revision_number

    def zip_article_files(self, filenames, new_filenames, zip_filename):
        """
        Move the files from old to new name into the tmp_dir
        add them to a zip file
        and move the zip file to the output_dir
        """

        # Move the files
        for filename in filenames:
            new_filename = new_filename_from_old(filename, new_filenames)
            if new_filename:
                old_filename_plus_path = os.path.join(
                    self.directories.get("INPUT_DIR"), filename
                )
                new_filename_plus_path = os.path.join(
                    self.directories.get("TMP_DIR"), new_filename
                )
                self.logger.info(
                    "moving poa file from %s to %s"
                    % (old_filename_plus_path, new_filename_plus_path)
                )

                shutil.move(old_filename_plus_path, new_filename_plus_path)

        # Repackage the PoA ds zip file
        self.repackage_poa_ds_zip()

        # Create the zip
        zip_filename_plus_path = os.path.join(
            self.directories.get("OUTPUT_DIR"), zip_filename
        )
        with zipfile.ZipFile(
            zip_filename_plus_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as new_zipfile:
            # Add the files
            for file in glob.glob("%s/*" % self.directories.get("TMP_DIR")):
                filename = file.split(os.sep)[-1]
                new_zipfile.write(file, filename)

        # Clean out the tmp_dir
        for file in glob.glob("%s/*" % self.directories.get("TMP_DIR")):
            filename = file.split(os.sep)[-1]
            new_filename_plus_path = os.path.join(
                self.directories.get("DONE_DIR"), filename
            )
            shutil.move(file, new_filename_plus_path)

    def repackage_poa_ds_zip(self):
        """
        If there is a ds zip file for this article files in the tmp_dir
        then repackage it
        """
        zipfiles = glob.glob("%s/*.zip" % self.directories.get("TMP_DIR"))
        if len(zipfiles) == 1:
            zipfile_file = zipfiles[0]
            zipfile_filename = zipfile_file.split(os.sep)[-1]
            with zipfile.ZipFile(zipfile_file, "r") as myzip:
                # New style zip file, if no manifest.xml file then leave the zip file alone
                if "manifest.xml" not in myzip.namelist():
                    myzip.close()
                    return

                # Extract the zip
                myzip.extractall(self.directories.get("TMP_DIR"))

            # Remove the manifest.xml file
            try:
                shutil.move(
                    os.path.join(self.directories.get("TMP_DIR"), "manifest.xml"),
                    os.path.join(self.directories.get("JUNK_DIR"), "manifest.xml"),
                )
                self.logger.info("moving PoA zip manifest.xml to the junk folder")
            except IOError:
                pass

            # Move the old zip file
            zipfiles_now = glob.glob("%s/*.zip" % self.directories.get("TMP_DIR"))
            for new_zipfile in zipfiles_now:
                if not new_zipfile.endswith("_Supplemental_files.zip"):
                    # Old zip file, move it to junk
                    new_zipfile_filename = new_zipfile.split(os.sep)[-1]
                    shutil.move(
                        new_zipfile,
                        os.path.join(
                            self.directories.get("JUNK_DIR"), new_zipfile_filename
                        ),
                    )

            # Then can rename the new zip file
            zipfiles_now = glob.glob("%s/*.zip" % self.directories.get("TMP_DIR"))
            for new_zipfile in zipfiles_now:
                if new_zipfile.endswith("_Supplemental_files.zip"):
                    # Rename the zip as the old zip
                    shutil.move(
                        new_zipfile,
                        os.path.join(self.directories.get("TMP_DIR"), zipfile_filename),
                    )

    def upload_files_to_s3(self):
        """
        Upload the article zip files to S3
        """

        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        self.logger.info("STARTING HERE")
        for file_path in glob.glob("%s/*.zip" % self.directories.get("OUTPUT_DIR")):
            file_name = file_path.split(os.sep)[-1]
            resource_dest = storage_provider + bucket_name + "/" + file_name
            storage.set_resource_from_filename(resource_dest, file_path)
            self.logger.info(
                "uploaded %s to s3 bucket path %s", (file_path, resource_dest)
            )
        return True

    def approve_for_publishing(self):
        """
        Final checks before processing the downloaded files
        Check for empty INPUT_DIR
        """
        # Check for empty directory
        if len(glob.glob("%s/*" % self.directories.get("INPUT_DIR"))) <= 1:
            return False
        return True

    def filter_ds_zip_files(self):
        "For each data supplements file, move invalid ones to not publish by FTP"
        zipfiles = glob.glob("%s/*_ds.zip" % self.directories.get("INPUT_DIR"))
        for input_zipfile in zipfiles:
            badfile = None
            filename = input_zipfile.split(os.sep)[-1]
            try:
                with zipfile.ZipFile(input_zipfile, "r") as current_zipfile:
                    filename = current_zipfile.filename.split(os.sep)[-1]
                    # Check for those with no zipped folder contents
                    if check_empty_supplemental_files(current_zipfile) is not True:
                        badfile = True
                        self.empty_ds_file_names.append(filename)

                    # Check for a file with no matching XML document
                    if (
                        check_matching_xml_file(
                            filename, self.directories.get("INPUT_DIR")
                        )
                        is not True
                        or check_matching_pdf_file(
                            filename, self.directories.get("INPUT_DIR")
                        )
                        is not True
                    ):
                        badfile = True
                        self.unmatched_ds_file_names.append(filename)
            except zipfile.BadZipfile:
                badfile = True
                self.malformed_ds_file_names.append(filename)
                current_zipfile = None

            if badfile:
                # File is not good, move it somewhere
                shutil.move(
                    os.path.join(self.directories.get("INPUT_DIR"), filename),
                    self.directories.get("JUNK_DIR") + "/",
                )

    def filter_file_pairs(self):
        """
        Remove files that should not be published due to incomplete
        sets of files per article
        """
        # For each xml or pdf file, check there is a matching pair
        xml_files = glob.glob("%s/*.xml" % self.directories.get("INPUT_DIR"))
        pdf_files = glob.glob("%s/*.pdf" % self.directories.get("INPUT_DIR"))

        for filename in xml_files:
            matching_filename = get_filename_from_path(filename, ".xml")
            pdf_filenames = [get_filename_from_path(f, ".pdf") for f in pdf_files]
            pdf_filenames = [fname.replace("decap_", "") for fname in pdf_filenames]

            if matching_filename not in pdf_filenames:
                shutil.move(filename, self.directories.get("JUNK_DIR") + "/")

        for filename in pdf_files:
            matching_filename = get_filename_from_path(filename, ".pdf")
            matching_filename = matching_filename.replace("decap_", "")
            xml_filenames = [
                get_filename_from_path(fname, ".xml") for fname in xml_files
            ]
            if matching_filename not in xml_filenames:
                shutil.move(filename, self.directories.get("JUNK_DIR") + "/")

    def send_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        activity_status_text = utils.get_activity_status_text(self.activity_status)

        statuses = {
            "activity": self.activity_status,
            "approve": self.approve_status,
            "publish": self.publish_status,
        }

        body = email_provider.get_email_body_head(
            self.name, activity_status_text, statuses
        )
        body += email_provider.get_email_body_middle_outbox_files(
            self.outbox_s3_key_names
        )
        body += self.get_email_body()
        body += email_provider.get_admin_email_body_foot(
            self.get_activityId(),
            self.get_workflowId(),
            datetime_string,
            self.settings.domain,
        )

        subject = email_provider.get_email_subject(
            datetime_string,
            activity_status_text,
            self.name,
            self.settings.domain,
            self.outbox_s3_key_names,
        )

        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_poa_recipient_email
        )

        for email in recipient_email_list:
            # send the email by SMTP
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger
            )

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger
            )
            self.logger.info(
                "Email sending details: admin email, email %s, to %s"
                % ("PublishFinalPOA", email)
            )

        return True

    def get_email_body(self):
        """
        Format the unique body of the email
        """

        body = ""

        if self.outbox_s3_key_names:
            # Report on any empty or unmatched supplement files
            if self.malformed_ds_file_names:
                body += "\nNote: Malformed ds files not sent by ftp: \n"
                for name in self.malformed_ds_file_names:
                    body += "%s\n" % name
            if self.empty_ds_file_names:
                body += "\nNote: Empty ds files not sent by ftp: \n"
                for name in self.empty_ds_file_names:
                    body += "%s\n" % name
            if self.unmatched_ds_file_names:
                body += "\nNote: Unmatched ds files not sent by ftp: \n"
                for name in self.unmatched_ds_file_names:
                    body += "%s\n" % name

        if self.publish_status is True and self.outbox_s3_key_names:
            body += "\nFiles moved to: %s\n" % str(self.published_folder_name)

        for name in self.clean_from_outbox_files:
            body += "%s\n" % name

        return body


def check_matching_xml_file(zip_filename, input_dir):
    """
    Given a zipfile.ZipFile object, check if for the DOI it represents
    there is a matching XML file for that DOI
    """
    zip_file_article_number = get_filename_from_path(zip_filename, "_ds.zip")

    xml_files = glob.glob("%s/*.xml" % input_dir)
    xml_file_articles_numbers = []
    for xml_file in xml_files:
        xml_file_articles_numbers.append(get_filename_from_path(xml_file, ".xml"))

    if zip_file_article_number in xml_file_articles_numbers:
        return True

    # Default return
    return False


def check_matching_pdf_file(zip_filename, input_dir):
    """
    Given a zipfile.ZipFile object, check if for the DOI it represents
    there is a matching PDF file for that DOI
    """
    zip_file_article_number = get_filename_from_path(zip_filename, "_ds.zip")

    pdf_files = glob.glob("%s/*.pdf" % input_dir)
    pdf_file_articles_numbers = []
    for file_name in pdf_files:
        pdf_file_name = get_filename_from_path(file_name, ".pdf")
        # Remove the decap_ from the start of the file name before comparing
        pdf_file_name = pdf_file_name.replace("decap_", "")
        pdf_file_articles_numbers.append(pdf_file_name)

    if zip_file_article_number in pdf_file_articles_numbers:
        return True

    # Default return
    return False


def profile_article_files(input_dir):
    """
    In the inbox, look for each article doi_id
    and the files associated with that article
    """
    article_filenames_map = {}

    for file_path in glob.glob("%s/*" % input_dir):
        filename = file_path.split(os.sep)[-1]
        doi_id = doi_id_from_filename(filename)
        if doi_id:
            # doi_id_str = utils.pad_msid(doi_id)
            if doi_id not in article_filenames_map:
                article_filenames_map[doi_id] = []
            # Add the filename to the map for this article
            article_filenames_map[doi_id].append(filename)

    return article_filenames_map


def create_new_filenames(doi_id, filenames):
    """
    Given a list of file names for one article,
    rename them
    Since there should only be one xml, pdf and possible zip
    this should be simple
    """
    new_filenames = []
    for filename in filenames:
        name_prefix = "elife-" + utils.pad_msid(doi_id)
        if filename.endswith(".xml"):
            new_filenames.append(name_prefix + ".xml")
        if filename.endswith(".pdf"):
            new_filenames.append(name_prefix + ".pdf")
        if filename.endswith(".zip"):
            new_filenames.append(name_prefix + "-supp.zip")
    return new_filenames


def doi_id_from_filename(filename):
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
    part = filename.replace("decap_elife_poa_e", "")
    part = part.replace("elife_poa_e", "")
    # Take the next five characters as digits
    try:
        doi_id = int(part[0:5])
    except (IndexError, ValueError):
        doi_id = None
    return doi_id


def article_xml_from_filename_map(filenames):
    """
    Given a list of file names, return the article xml file name
    """
    for file_name in filenames:
        if file_name.endswith(".xml"):
            return file_name
    return None


def article_soup(xml_file):
    return parser.parse_document(xml_file)


def get_pub_date_if_missing(doi_id, settings, logger):
    # Get the date for the first version
    date_struct = None
    date_str = get_pub_date_str_from_lax(doi_id, settings, logger)

    if date_str is not None:
        date_struct = time.strptime(date_str, "%Y%m%d000000")
    else:
        # Use current date
        date_struct = time.gmtime()
    return date_struct


def get_pub_date_str_from_lax(doi_id, settings, logger):
    """
    Check lax for any article published version
    If found, get the pub date and format it as a string YYYYMMDDhhmmss
    """
    article_id = utils.pad_msid(doi_id)
    return lax_provider.article_publication_date(article_id, settings, logger)


def convert_xml(doi_id, xml_file, new_filenames, settings, logger):

    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    soup = article_soup(xml_file)

    if parser.is_poa(soup):
        pub_date = None
        if parser.pub_date(soup) is None:
            # add the published date to the XML
            pub_date = get_pub_date_if_missing(doi_id, settings, logger)
            root = add_pub_date_to_xml(doi_id, pub_date, root, logger)
        else:
            pub_date = parser.pub_date(soup)

        if parser.volume(soup) is None:
            # Get the pub-date year to calculate the volume
            year = pub_date[0]
            volume = year - 2011
            add_volume_to_xml(doi_id, volume, root, logger)

        # set the article-id, to overwrite the v2, v3 value if present
        root = set_article_id_xml(doi_id, root)

        # if pdf file then add self-uri tag
        if parser.self_uri(soup) is not None and not parser.self_uri(soup):
            for filename in new_filenames:
                if filename.endswith(".pdf"):
                    root = add_self_uri_to_xml(doi_id, filename, root, logger)

        # if ds.zip file is there, then add it to the xml
        poa_ds_zip_file = None
        for new_file in new_filenames:
            if new_file.endswith(".zip"):
                poa_ds_zip_file = new_file
        if poa_ds_zip_file:
            root = add_poa_ds_zip_to_xml(poa_ds_zip_file, root)

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    # Remove extra whitespace here for PoA articles to clean up and one VoR file too
    reparsed_string = reparsed_string.replace(b"\n", b"").replace(b"\t", b"")

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)


def modify_xml(xml_file, doi_id, new_filenames, settings, logger):
    "Convert the XML file with exception handling"
    try:
        convert_xml(doi_id, xml_file, new_filenames, settings, logger)
    except Exception as exception:
        # One possible error is an entirely blank XML file or a malformed xml file
        logger.exception(
            "Exception when converting XML for doi %s, %s" % (str(doi_id), exception)
        )
        return False
    return True


def add_self_uri_to_xml(doi_id, file_name, root, logger):
    """
    Add the self-uri tag to the XML for the PDF file
    """

    # Create the XML tag
    self_uri_tag = self_uri_xml_element(file_name)

    # Add the tag to the XML
    for tag in root.findall("./front/article-meta"):
        parent_tag_index = xmlio.get_first_element_index(tag, "permissions")
        if not parent_tag_index:
            logger.info("no permissions tag and no self-uri tag added: %s", doi_id)
        else:
            tag.insert(parent_tag_index, self_uri_tag)

    return root


def add_tag_to_xml_before_elocation_id(add_tag, root, doi_id, logger):
    # Add the tag to the XML
    for tag in root.findall("./front/article-meta"):
        parent_tag_index = xmlio.get_first_element_index(tag, "elocation-id")
        if not parent_tag_index:
            logger.info(
                "no elocation-id tag and no %s added: %s", (add_tag.tag, doi_id)
            )
        else:
            tag.insert(parent_tag_index - 1, add_tag)

        # Should only do it once but ensure it is only done once
        break
    return root


def add_pub_date_to_xml(doi_id, date_struct, root, logger):
    # Create the pub-date XML tag
    pub_date_tag = pub_date_xml_element(date_struct)
    root = add_tag_to_xml_before_elocation_id(pub_date_tag, root, doi_id, logger)
    return root


def add_volume_to_xml(doi_id, volume, root, logger):
    # Create the pub-date XML tag
    volume_tag = volume_xml_element(volume)
    root = add_tag_to_xml_before_elocation_id(volume_tag, root, doi_id, logger)
    return root


def pub_date_xml_element(pub_date):

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


def volume_xml_element(volume):
    volume_tag = Element("volume")
    volume_tag.text = str(volume)
    return volume_tag


def set_article_id_xml(doi_id, root):

    for tag in root.findall("./front/article-meta/article-id"):
        if tag.get("pub-id-type") == "publisher-id":
            # Overwrite the text with the base DOI value
            tag.text = utils.pad_msid(doi_id)

    return root


def add_poa_ds_zip_to_xml(file_name, root):
    """
    Add the ext-link tag to the XML for the PoA ds.zip file
    """

    # Create the XML tag
    supp_tag = ds_zip_xml_element(file_name)

    # Add the tag to the XML
    back_sec_tags = root.findall('./back/sec[@sec-type="supplementary-material"]')
    if not back_sec_tags:
        # add sec tag
        back_tags = root.findall("./back")
        back_tag = back_tags[0]
        sec_tag = SubElement(back_tag, "sec")
        sec_tag.set("sec-type", "supplementary-material")
    else:
        sec_tag = back_sec_tags[-1]

    sec_tag.append(supp_tag)

    return root


def ds_zip_xml_element(file_name):

    supp_tag = Element("supplementary-material")
    ext_link_tag = SubElement(supp_tag, "ext-link")
    ext_link_tag.set("xlink:href", file_name)
    if "supp" in file_name:
        ext_link_tag.text = "Download zip"

        p_tag = SubElement(supp_tag, "p")
        p_tag.text = (
            "Any figures and tables for this article are included "
            + "in the PDF. The zip folder contains additional supplemental files."
        )

    return supp_tag


def self_uri_xml_element(file_name):
    self_uri_tag = Element("self-uri")
    self_uri_tag.set("content-type", "pdf")
    self_uri_tag.set("xlink:href", file_name)
    return self_uri_tag


def new_zip_file_name(doi_id, revision, status="poa"):
    return "elife-%s-%s-r%s.zip" % (utils.pad_msid(doi_id), status, revision)


def new_filename_from_old(old_filename, new_filenames):
    """
    From a list of new file names, find the new name
    that corresponds with the old file name based on the file extension
    """
    new_filename = None
    try:
        extension = old_filename.split(".")[-1]
    except AttributeError:
        extension = None
    if extension:
        for filename in new_filenames:
            new_extension = filename.split(".")[-1]
            if new_extension and extension == new_extension:
                new_filename = filename
    return new_filename


def check_empty_supplemental_files(input_zipfile):
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
    if not sub_folder_name and input_zipfile.namelist():
        return True

    if sub_folder_name:
        zipextfile = input_zipfile.open(sub_folder_name)

        while zipextfile.readline():
            zipextfile_line_count += 1

    # Empty subfolder zipextfile object will have only 1 line
    #  Non-empty file will have more than 1 line
    if zipextfile_line_count <= 1:
        return False
    return True


def get_filename_from_path(file_path, extension):
    """
    Get a filename minus the supplied file extension
    and without any folder or path
    """
    filename = file_path.split(extension)[0]
    # Remove path if present
    filename = filename.split(os.sep)[-1]
    return filename
