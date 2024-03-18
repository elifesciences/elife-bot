import os
import copy
import json
import time
import glob
from collections import OrderedDict
from activity.objects import Activity
from provider import (
    cleaner,
    crossref,
    email_provider,
    lax_provider,
    outbox_provider,
    utils,
)


class activity_DepositCrossrefPostedContent(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DepositCrossrefPostedContent, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DepositCrossrefPostedContent"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download article XML from S3 bucket outbox, "
            + "generate Crossref posted_content deposit XML, and deposit with Crossref."
        )

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder(self.name)
        )
        self.published_folder = outbox_provider.published_folder(
            self.s3_bucket_folder(self.name)
        )
        self.not_published_folder = outbox_provider.not_published_folder(
            self.s3_bucket_folder(self.name)
        )

        # Track the success of some steps
        self.statuses = {}

        # Track XML files selected for pubmed XML
        self.good_xml_files = []
        self.bad_xml_files = []
        self.not_published_xml_files = []

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        # override the crossref.generate TMP_DIR first
        crossref.override_tmp_dir(self.directories.get("TMP_DIR"))

        date_stamp = utils.set_datestamp()

        outbox_s3_key_names = outbox_provider.get_outbox_s3_key_names(
            self.settings, self.publish_bucket, self.outbox_folder
        )

        # Download the S3 objects
        self.statuses["download"] = outbox_provider.download_files_from_s3_outbox(
            self.settings,
            self.publish_bucket,
            outbox_s3_key_names,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )

        article_xml_files = glob.glob(self.directories.get("INPUT_DIR") + "/*.xml")

        crossref_config = crossref.elifecrossref_preprint_config(self.settings)
        crossref_version_config = crossref.elifecrossref_preprint_version_config(
            self.settings
        )

        article_object_map = self.get_article_objects(article_xml_files)

        # build Crossref deposit objects
        crossref_object_map = OrderedDict()
        for xml_file, article in list(article_object_map.items()):
            # check for a published POA or VOR version before adding the concept DOI deposit
            status_version_map = lax_provider.article_status_version_map(
                article.manuscript, self.settings
            )
            if len(status_version_map.keys()) > 0:
                # there is already a poa or vor, skip it
                self.logger.info(
                    "%s, there is already a VOR article published for article.manuscript,"
                    " will not generate a concept DOI deposit" % self.name
                )
                continue

            # check whether this is a less than more recent EPP version
            docmap_string = cleaner.get_docmap_string(
                self.settings,
                article.manuscript,
                article.manuscript,
                self.name,
                self.logger,
            )
            newest_version_doi = cleaner.version_doi_from_docmap(
                docmap_string, article.manuscript
            )
            if newest_version_doi != article.version_doi:
                self.logger.info(
                    "%s, the article version DOI %s does not equal the docmap version DOI %s,"
                    " will not generate a concept DOI deposit"
                    % (self.name, article.version_doi, newest_version_doi)
                )
                continue

            crossref_object_list = crossref.build_crossref_xml(
                {xml_file: article},
                crossref_config,
                self.good_xml_files,
                self.bad_xml_files,
                submission_type="posted_content",
            )
            if crossref_object_list[0]:
                crossref_object_map[article] = crossref_object_list[0]

        # duplicate and modify the article for a version_doi deposit, set a different batch_id
        for xml_file, article in list(article_object_map.items()):
            if article.version_doi:
                # track a separate list of good and bad files later to be collated
                good_xml_files = []
                bad_xml_files = []
                article_version = copy.copy(article)
                article_version.doi = article_version.version_doi
                article_version.version_doi = None
                # generate CrossrefXML
                crossref_object_list = crossref.build_crossref_xml(
                    {xml_file: article_version},
                    crossref_version_config,
                    good_xml_files,
                    bad_xml_files,
                    submission_type="posted_content",
                )
                # collate good and bad files
                self.good_xml_files = list(
                    set(self.good_xml_files).union(set(good_xml_files))
                )
                self.bad_xml_files = list(
                    set(self.bad_xml_files).union(set(bad_xml_files))
                )
                # add the CrossrefXML
                if crossref_object_list[0]:
                    # change the batch_id
                    crossref_object_list[0].batch_id = crossref_object_list[
                        0
                    ].batch_id.replace(
                        "elife-crossref-preprint-posted_content-",
                        "elife-crossref-preprint-posted_content-version-",
                    )
                    crossref_object_map[article_version] = crossref_object_list[0]

        # generate status will be True if no unhandled exception was raised
        self.statuses["generate"] = True

        # output CrossrefXML objects to XML files
        for article, c_xml in list(crossref_object_map.items()):
            if article.version_doi:
                # add rel:program tag if not present
                crossref.add_posted_content_rel_program_tag(c_xml.root)
                # find the rel:program tag
                rel_program_tag = crossref.find_posted_content_rel_program_tag(
                    c_xml.root
                )
                if article.version_doi:
                    # add intra_work_relation isSameAs tag
                    crossref.add_is_same_as_tag(rel_program_tag, article.version_doi)

            crossref.crossref_xml_to_disk(
                c_xml, self.directories.get("TMP_DIR"), pretty=True
            )

        # Approve files for publishing
        self.statuses["approve"] = self.approve_for_publishing()

        http_detail_list = []
        if self.statuses.get("approve") is True:
            file_type = "/*.xml"
            sub_dir = self.directories.get("TMP_DIR")
            try:
                # Publish files
                (
                    self.statuses["publish"],
                    http_detail_list,
                ) = self.deposit_files_to_endpoint(file_type, sub_dir)
            except:
                self.logger.info(
                    "Exception publishing files to Crossref: %s"
                    % glob.glob(sub_dir + file_type)
                )
                self.statuses["publish"] = False

        if self.statuses.get("publish") is True:
            # Clean up outbox
            self.logger.info("Moving files from outbox folder to published folder")
            to_folder = outbox_provider.get_to_folder_name(
                self.published_folder, date_stamp
            )
            outbox_provider.clean_outbox(
                self.settings,
                self.publish_bucket,
                self.outbox_folder,
                to_folder,
                self.good_xml_files,
            )
            # copy the Crossref deposit XML files to the batch folder
            batch_file_names = glob.glob(self.directories.get("TMP_DIR") + "/*.xml")
            batch_file_to_folder = to_folder + "batch/"
            outbox_provider.upload_files_to_s3_folder(
                self.settings,
                self.publish_bucket,
                batch_file_to_folder,
                batch_file_names,
            )
            # move files if the DOI already exists to out of the outbox folder
            self.logger.info(
                "Moving files from outbox folder to the not_published folder"
            )
            not_published_to_folder = outbox_provider.get_to_folder_name(
                self.not_published_folder, date_stamp
            )
            outbox_provider.clean_outbox(
                self.settings,
                self.publish_bucket,
                self.outbox_folder,
                not_published_to_folder,
                self.not_published_xml_files,
            )

            self.statuses["outbox"] = True
        else:
            self.logger.info(
                "Failed to publish all posted content deposits to Crossref"
            )

        # Set the activity status of this activity based on successes
        self.statuses["activity"] = bool(
            self.statuses.get("publish") is not False
            and self.statuses.get("generate") is not False
        )

        # Send email
        # Only if there were files approved for publishing
        if self.good_xml_files:
            self.statuses["email"] = self.send_admin_email(
                outbox_s3_key_names, http_detail_list
            )
        else:
            self.logger.info(
                "No Crossref deposit files generated in %s. bad_xml_files: %s"
                % (self.name, self.bad_xml_files)
            )

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # sleep if there was a deposit
        if self.good_xml_files and data and data.get("sleep_seconds"):
            self.logger.info(
                "%s sleeping %s seconds after the deposit"
                % (self.name, data.get("sleep_seconds"))
            )
            time.sleep(data.get("sleep_seconds"))

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def get_article_objects(self, article_xml_files):
        """turn XML into article objects and populate their data"""
        # parse XML files into the basic article object map to start with
        article_object_map = crossref.article_xml_list_parse(
            article_xml_files, self.bad_xml_files, self.directories.get("TMP_DIR")
        )
        return article_object_map

    def approve_for_publishing(self):
        """check if any files were generated before publishing files to the endpoint"""
        return bool(glob.glob(self.directories.get("INPUT_DIR") + "/*.xml"))

    def deposit_files_to_endpoint(self, file_type="/*.xml", sub_dir=None):
        """Using an HTTP POST, deposit the file to the endpoint"""
        xml_files = glob.glob(sub_dir + file_type)
        if not xml_files:
            return None
        payload = crossref.crossref_data_payload(
            self.settings.crossref_login_id, self.settings.crossref_login_passwd
        )
        return crossref.upload_files_to_endpoint(
            self.settings.crossref_url, payload, xml_files
        )

    def send_admin_email(self, outbox_s3_key_names, http_detail_list):
        """
        After do_activity is finished, send emails to recipients
        on the status
        """
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        activity_status_text = utils.get_activity_status_text(
            self.statuses.get("activity")
        )

        body = email_provider.get_email_body_head(
            self.name, activity_status_text, self.statuses
        )
        body += email_provider.get_email_body_middle(
            self.s3_bucket_folder(self.name),
            outbox_s3_key_names,
            self.good_xml_files,
            self.bad_xml_files,
            http_detail_list,
            self.not_published_xml_files,
        )
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
            outbox_s3_key_names,
        )
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email
        )

        for email in recipient_email_list:
            # Add the email to the email queue
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger
            )

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger
            )
            self.logger.info(
                "Email sending details: admin email, email %s, to %s"
                % ("DepositCrossrefPostedContent", email)
            )

        return True
