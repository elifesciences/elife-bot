import os
import json
import time
import glob
from collections import OrderedDict
from elifearticle.article import ArticleDate
from activity.objects import Activity
from provider import (
    bigquery,
    crossref,
    email_provider,
    lax_provider,
    outbox_provider,
    utils,
)


class activity_DepositCrossrefPeerReview(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositCrossrefPeerReview, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "DepositCrossrefPeerReview"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download article XML from S3 bucket outbox, "
            + "generate Crossref peer review deposit XML, and deposit with Crossref."
        )

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "crossref_peer_review/outbox/"
        self.published_folder = "crossref_peer_review/published/"

        # Track the success of some steps
        self.statuses = {}

        # Track XML files selected for pubmed XML
        self.good_xml_files = []
        self.bad_xml_files = []

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

        crossref_config = crossref.elifecrossref_config(self.settings)

        article_object_map = self.get_article_objects(article_xml_files)

        generate_article_object_map = prune_article_object_map(
            article_object_map, self.settings, self.logger
        )

        # Generate crossref XML
        self.statuses["generate"] = crossref.generate_crossref_xml_to_disk(
            generate_article_object_map,
            crossref_config,
            self.good_xml_files,
            self.bad_xml_files,
            submission_type="peer_review",
            pretty=True,
            indent="    ",
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
            self.statuses["outbox"] = True
        else:
            self.logger.info("Failed to publish all peer review deposits to Crossref")

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

        return True

    def get_article_objects(self, article_xml_files):
        """turn XML into article objects and populate their data"""
        # parse XML files into the basic article object map to start with
        article_object_map = crossref.article_xml_list_parse(
            article_xml_files, self.bad_xml_files, self.directories.get("TMP_DIR")
        )
        # continue with setting more article data
        for article in list(article_object_map.values()):
            # populate Manuscript object
            manuscript_object = self.get_manuscript_object(article.doi)

            for sub_article in article.review_articles:
                # add editor / reviewer / senior_editor records from the parent article if missing
                if sub_article.article_type not in ["editor-report", "reply"]:
                    self.add_editors(article, sub_article)

                # set missing ORCID values for editors
                if sub_article.article_type != "reply":
                    self.set_editor_orcid(sub_article, manuscript_object)

                # add review_date
                review_date = bigquery.get_review_date(
                    manuscript_object, sub_article.article_type
                )
                if review_date:
                    date_struct = time.strptime(review_date, utils.PUB_DATE_FORMAT)
                    review_date_object = ArticleDate("review_date", date_struct)
                    sub_article.add_date(review_date_object)
                # set author response author contrib values
                if sub_article.article_type == "reply" and not sub_article.contributors:
                    sub_article.contributors = [
                        contrib
                        for contrib in article.contributors
                        if contrib.contrib_type == "author"
                    ]
                # fix editor roles
                change_editor_roles(sub_article)
                # dedupe contributors
                dedupe_contributors(sub_article)

        return article_object_map

    def get_manuscript_object(self, doi):
        """get data from BigQuery and populate a Manuscript object"""
        bigquery_client = bigquery.get_client(self.settings, self.logger)
        rows = bigquery.article_data(bigquery_client, doi)
        # use the first row returned
        try:
            first_row = [row for row in rows][0]
        except IndexError:
            first_row = None
            self.logger.info("No data from BigQuery for DOI %s" % doi)
        return bigquery.Manuscript(first_row)

    def add_editors(self, article, sub_article):
        """add editors from article to sub_article if they are not already present"""
        for contrib in article.editors:
            # compare three matching parts: contrib_type, surname, and given_name
            if (contrib.contrib_type, contrib.surname, contrib.given_name) not in [
                (obj.contrib_type, obj.surname, obj.given_name)
                for obj in sub_article.contributors
            ]:
                # append it
                sub_article.contributors.append(contrib)
                self.logger.info(
                    "Added %s %s from parent article to decision letter"
                    % (contrib.contrib_type, contrib.surname)
                )

    def set_editor_orcid(self, sub_article, manuscript_object):
        for contrib in sub_article.contributors:
            if not contrib.orcid:
                for reviewer in manuscript_object.reviewers:
                    # match on surname and first initial
                    if (
                        reviewer.orcid
                        and contrib.surname == reviewer.last_name
                        and contrib.given_name
                        and reviewer.first_name
                        and contrib.given_name[0] == reviewer.first_name[0]
                    ):
                        orcid_uri = "https://orcid.org/" + reviewer.orcid
                        contrib.orcid = orcid_uri
                        self.logger.info(
                            "Set ORCID for %s to %s in %s"
                            % (contrib.surname, orcid_uri, sub_article.doi)
                        )

    def approve_for_publishing(self):
        """check if any files were generated before publishing files to the endpoint"""
        return bool(glob.glob(self.directories.get("INPUT_DIR") + "/*.xml"))

    def deposit_files_to_endpoint(self, file_type="/*.xml", sub_dir=None):
        """Using an HTTP POST, deposit the file to the endpoint"""
        xml_files = glob.glob(sub_dir + file_type)
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
            "crossref",
            outbox_s3_key_names,
            self.good_xml_files,
            self.bad_xml_files,
            http_detail_list,
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
                % ("DepositCrossrefPeerReview", email)
            )

        return True


def prune_article_object_map(article_object_map, settings, logger):
    """remove any articles from the map that should not be deposited as peer reviews"""
    # prune any articles with no review_articles
    good_article_object_map = OrderedDict()
    for file_name, article in article_object_map.items():
        good = True
        # check it has review articles
        good = has_review_articles(article, logger)
        # check DOI exists
        if good:
            good = check_doi_exists(article, logger)
        # check VoR is published
        if good:
            good = check_vor_is_published(article, settings, logger)

        # finally if still good, add it to the map of good articles
        if good:
            good_article_object_map[file_name] = article

    return good_article_object_map


def has_review_articles(article, logger):
    if article.review_articles:
        return True
    logger.info(
        "Pruning article %s from Crossref peer review deposit, it has no peer reviews"
        % article.doi
    )
    return False


def check_doi_exists(article, logger):
    if crossref.doi_exists(article.doi, logger):
        return True
    logger.info(
        "Pruning article %s from Crossref peer review deposit, DOI does not exist"
        % article.doi
    )
    return False


def check_vor_is_published(article, settings, logger):
    status_version_map = lax_provider.article_status_version_map(
        article.manuscript, settings
    )
    if "vor" in status_version_map:
        return True
    logger.info(
        "Pruning article %s from Crossref peer review deposit, VoR is not published"
        ", version map: %s" % (article.doi, status_version_map)
    )
    return False


def change_editor_roles(article):
    """Crossref does not accept senior_editor, change it"""
    for contrib in article.contributors:
        # change senior_editor to editor, if present
        if contrib.contrib_type == "senior_editor":
            contrib.contrib_type = "editor"


def dedupe_contributors(article):
    """add each contributor only once if there are duplicates"""
    contributors = []
    contrib_seen = []
    for contrib in article.contributors:
        contrib_match = "%s,%s,%s" % (
            contrib.surname,
            contrib.given_name,
            contrib.contrib_type,
        )
        if contrib_match not in contrib_seen:
            contributors.append(contrib)
            contrib_seen.append(contrib_match)
    # reset the article contributors to the deduped list
    article.contributors = contributors
