import os
import json
import time
import glob
import requests
from activity.objects import Activity
from provider.storage_provider import storage_context
from provider import article_processing, crossref, email_provider, lax_provider, utils
from elifecrossref import generate

"""
DepositCrossref activity
"""


class activity_DepositCrossref(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositCrossref, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "DepositCrossref"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = ("Download article XML from crossref outbox, " +
                            "generate crossref XML, and deposit with crossref.")

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "crossref/outbox/"
        self.published_folder = "crossref/published/"

        # Track the success of some steps
        self.statuses = {}

        # Track XML files selected for pubmed XML
        self.article_published_file_names = []
        self.article_not_published_file_names = []

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        date_stamp = utils.set_datestamp()

        outbox_s3_key_names = self.get_outbox_s3_key_names()

        # Download the S3 objects
        self.download_files_from_s3_outbox(outbox_s3_key_names)

        # Generate crossref XML
        self.statuses["generate"] = self.generate_crossref_xml()

        # Approve files for publishing
        self.statuses["approve"] = self.approve_for_publishing()

        http_detail_list = []
        if self.statuses.get("approve") is True:
            try:
                # Publish files
                self.statuses["publish"], http_detail_list = self.deposit_files_to_endpoint(
                    sub_dir=self.directories.get("TMP_DIR"))
            except:
                self.statuses["publish"] = False

            if self.statuses.get("publish") is True:
                # Clean up outbox
                self.logger.info("Moving files from outbox folder to published folder")
                self.clean_outbox(self.article_published_file_names, date_stamp)
                self.upload_crossref_xml_to_s3(date_stamp)
                self.statuses["outbox"] = True

        # Set the activity status of this activity based on successes
        self.statuses["activity"] = bool(
            self.statuses.get("publish") is not False and
            self.statuses.get("generate") is not False)

        # Send email
        # Only if there were files approved for publishing
        if len(self.article_published_file_names) > 0:
            self.statuses["email"] = self.send_admin_email(outbox_s3_key_names, http_detail_list)

        self.logger.info(
            "%s statuses: %s" % (self.name, self.statuses))

        return True

    def download_files_from_s3_outbox(self, outbox_s3_key_names):
        """from the s3 outbox folder,  download the .xml files"""
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + self.publish_bucket + "/"

        for name in outbox_s3_key_names:
            # Download objects from S3 and save to disk
            file_name = name.split('/')[-1]
            file_path = os.path.join(self.directories.get("INPUT_DIR"), file_name)
            storage_resource_origin = orig_resource + '/' + name
            try:
                with open(file_path, 'wb') as open_file:
                    self.logger.info("Downloading %s to %s", (storage_resource_origin, file_path))
                    storage.get_resource_to_file(storage_resource_origin, open_file)
            except IOError:
                self.logger.exception("Failed to download file %s.", name)
                return False
        return True

    def get_article_list(self, article_xml_files):
        """turn XML into article objects and populate their data"""
        articles = crossref.parse_article_xml(article_xml_files, self.directories.get("TMP_DIR"))
        crossref_config = crossref.elifecrossref_config(self.settings)
        for article in articles:
            # Check for a pub date otherwise set one
            crossref.set_article_pub_date(article, crossref_config, self.settings, self.logger)
            # Check for a version number
            crossref.set_article_version(article, self.settings)
        return articles

    def generate_crossref_xml(self):
        """
        Using the POA generateCrossrefXml module
        """
        article_xml_files = glob.glob(self.directories.get("INPUT_DIR") + "/*.xml")
        crossref_config = crossref.elifecrossref_config(self.settings)

        for xml_file in article_xml_files:
            generate_status = True

            # Convert the single value to a list for processing
            xml_files = [xml_file]
            article_list = self.get_article_list(xml_files)

            if len(article_list) == 0:
                self.article_not_published_file_names.append(xml_file)
                continue
            else:
                article = article_list[0]

            if crossref.approve_to_generate(crossref_config, article) is not True:
                generate_status = False
            else:
                try:
                    # Will write the XML to the TMP_DIR
                    generate.crossref_xml_to_disk(article_list, crossref_config)
                except:
                    generate_status = False

            if generate_status is True:
                # Add filename to the list of published files
                self.article_published_file_names.append(xml_file)
            else:
                # Add the file to the list of not published articles, may be used later
                self.article_not_published_file_names.append(xml_file)

        # Any files generated is a sucess, even if one failed
        return True

    def approve_for_publishing(self):
        """
        Final checks before publishing files to the endpoint
        """
        status = None

        # Check for empty directory
        article_xml_files = glob.glob(self.directories.get("INPUT_DIR") + "/*.xml")
        if len(article_xml_files) <= 0:
            status = False
        else:
            # Default until full sets of files checker is built
            status = True

        return status

    def deposit_files_to_endpoint(self, file_type="/*.xml", sub_dir=None):
        """
        Using an HTTP POST, deposit the file to the endpoint
        """

        # Default return status
        status = True
        http_detail_list = []

        url = self.settings.crossref_url
        payload = {'operation': 'doMDUpload',
                   'login_id': self.settings.crossref_login_id,
                   'login_passwd': self.settings.crossref_login_passwd
                  }

        # Crossref XML, can be multiple files to deposit
        xml_files = glob.glob(sub_dir + file_type)

        for xml_file in xml_files:
            files = {'file': open(xml_file, 'rb')}

            response = requests.post(url, data=payload, files=files)

            # Check for good HTTP status code
            if response.status_code != 200:
                status = False
            # print response.text
            http_detail_list.append("XML file: " + xml_file)
            http_detail_list.append("HTTP status: " + str(response.status_code))
            http_detail_list.append("HTTP response: " + response.text)

        return status, http_detail_list

    def get_outbox_s3_key_names(self):
        """get a list of .xml S3 key names from the outbox"""
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = (
            storage_provider + self.publish_bucket + "/" + self.outbox_folder.rstrip('/'))
        s3_key_names = storage.list_resources(orig_resource)
        # return only the .xml files
        return [key_name for key_name in s3_key_names if key_name.endswith('.xml')]

    def get_to_folder_name(self, date_stamp):
        """
        From the date_stamp
        return the S3 folder name to save published files into
        """
        return self.published_folder + date_stamp + "/"

    def clean_outbox(self, published_file_names, date_stamp):
        """Clean out the S3 outbox folder"""

        bucket_name = self.publish_bucket
        to_folder = self.get_to_folder_name(date_stamp)

        # Concatenate the expected S3 outbox file names
        s3_key_names = []
        for name in published_file_names:
            filename = name.split(os.sep)[-1]
            s3_key_name = self.outbox_folder + filename
            s3_key_names.append(s3_key_name)

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"

        for name in s3_key_names:
            # Do not delete the from_folder itself, if it is in the list
            if name == self.outbox_folder:
                continue
            filename = name.split("/")[-1]
            new_s3_key_name = to_folder + filename

            orig_resource = storage_provider + bucket_name + "/" + name
            dest_resource = storage_provider + bucket_name + "/" + new_s3_key_name

            # First copy
            storage.copy_resource(orig_resource, dest_resource)

            # Then delete the old key if successful
            storage.delete_resource(orig_resource)

    def upload_crossref_xml_to_s3(self, date_stamp):
        """
        Upload a copy of the crossref XML to S3 for reference
        """
        bucket_name = self.publish_bucket
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        s3_folder_name = self.published_folder + date_stamp + "/" + "batch/"

        for file_name in glob.glob(self.directories.get("TMP_DIR") + "/*.xml"):
            resource_dest = (
                storage_provider + bucket_name + "/" + s3_folder_name +
                article_processing.file_name_from_name(file_name))
            storage.set_resource_from_filename(resource_dest, file_name)

    def send_admin_email(self, outbox_s3_key_names, http_detail_list):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        datetime_string = time.strftime('%Y-%m-%d %H:%M', time.gmtime())
        activity_status_text = utils.get_activity_status_text(self.statuses.get("activity"))

        body = get_email_body_head(self.name, activity_status_text, self.statuses)
        body += get_email_body_middle(
            outbox_s3_key_names, self.article_published_file_names,
            self.article_not_published_file_names, http_detail_list)
        body += email_provider.get_admin_email_body_foot(
            self.get_activityId(), self.get_workflowId(), datetime_string, self.settings.domain)

        subject = get_email_subject(
            datetime_string, activity_status_text, self.name,
            self.settings.domain, outbox_s3_key_names)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger)

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)
            self.logger.info('Email sending details: admin email, email %s, to %s' %
                             ("DepositCrossref", email))

        return True


def get_email_subject(datetime_string, activity_status_text, name, domain, outbox_s3_key_names):
    """
    Assemble the email subject
    """
    # Count the files moved from the outbox, the files that were processed
    files_count = 0
    if outbox_s3_key_names:
        files_count = len(outbox_s3_key_names)

    subject = (
        name + " " + activity_status_text + " files: " + str(files_count) +
        ", " + datetime_string + ", eLife SWF domain: " + domain)

    return subject


def get_email_body_head(name, activity_status_text, statuses):
    """
    Format the body of the email
    """

    body = ""

    # Bulk of body
    body += name + " status:" + "\n"
    body += "\n"
    body += activity_status_text + "\n"
    body += "\n"

    body += "activity_status: " + str(statuses.get("activity")) + "\n"
    body += "generate_status: " + str(statuses.get("generate")) + "\n"
    body += "approve_status: " + str(statuses.get("approve")) + "\n"
    body += "publish_status: " + str(statuses.get("publish")) + "\n"
    body += "outbox_status: " + str(statuses.get("outbox")) + "\n"

    body += "\n"

    return body


def get_email_body_middle(outbox_s3_key_names, published_file_names,
                          not_published_file_names, http_detail_list):
    """
    Format the body of the email
    """

    body = ""

    body += "\n"
    body += "Outbox files: " + "\n"

    files_count = 0
    if outbox_s3_key_names:
        files_count = len(outbox_s3_key_names)
    if files_count > 0:
        for name in outbox_s3_key_names:
            body += name + "\n"
    else:
        body += "No files in outbox." + "\n"

    # Report on published files
    if len(published_file_names) > 0:
        body += "\n"
        body += "Published files generated crossref XML: " + "\n"
        for name in published_file_names:
            body += name.split(os.sep)[-1] + "\n"

    # Report on not published files
    if len(not_published_file_names) > 0:
        body += "\n"
        body += "Files not approved or failed crossref XML: " + "\n"
        for name in not_published_file_names:
            body += name.split(os.sep)[-1] + "\n"

    body += "\n"
    body += "-------------------------------\n"
    body += "HTTP deposit details: " + "\n"
    for text in http_detail_list:
        body += str(text) + "\n"

    return body
