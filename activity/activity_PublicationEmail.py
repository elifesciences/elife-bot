import json
import time
import os
import re
import arrow
from provider import ejp, email_provider, lax_provider, templates, utils
import provider.article as articlelib
from provider.storage_provider import storage_context
from activity.objects import Activity


# Article types for which not to send emails
ARTICLE_TYPES_DO_NOT_SEND = ['editorial', 'correction', 'retraction']


class activity_PublicationEmail(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PublicationEmail, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "PublicationEmail"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Queue emails to notify of a new article publication."

        # Templates provider
        self.templates = templates.Templates(settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "publication_email/outbox/"
        self.published_folder = "publication_email/published/"

        # Track the success of some steps
        self.activity_status = None

        # Track XML files selected for publication
        self.xml_file_to_doi_map = {}
        self.related_articles = []
        self.insight_articles_to_remove_from_outbox = []
        self.articles_do_not_remove_from_outbox = []

        self.admin_email_content = ''

    def do_activity(self, data=None):
        """
        PublicationEmail activity, do the work
        """

        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            # Download templates
            templates_downloaded = self.download_templates()
        except Exception:
            self.logger.exception("Failed to download templates")
            return self.ACTIVITY_PERMANENT_FAILURE
        if not templates_downloaded:
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            # Download the article XML from S3 and parse them
            article_xml_filenames = self.download_files_from_s3_outbox()
        except Exception:
            self.logger.exception("Failed to download files from the S3 outbox")
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            approved, prepared = self.process_articles(article_xml_filenames)
        except Exception:
            self.logger.exception("Failed to parse, approve, and prepare all the articles")
            return self.ACTIVITY_PERMANENT_FAILURE

        # return now if no articles are approved
        if not approved:
            self.logger.info("No articles were approved for sending")
            self.send_admin_email()
            return True

        try:
            self.send_emails_for_articles(prepared)

            # Clean the outbox
            self.clean_outbox(prepared)

            # Send email to admins with the status
            self.activity_status = True
            self.send_admin_email()
        except Exception:
            self.logger.exception("An error occured on do_activity method.")

        return True

    def log_cannot_find_authors(self, doi):
        log_info = ("Leaving article in the outbox because we cannot " +
                    "find its authors: " + doi)
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
        # Make a note of this and we will not remove from the outbox, save for a later day
        self.articles_do_not_remove_from_outbox.append(doi)

    def process_articles(self, article_xml_filenames):
        """multi-step parsing, approving, and preparing of article files"""
        articles = self.parse_article_xml(article_xml_filenames)
        approved = self.approve_articles(articles)
        prepared = self.prepare_articles(approved)

        log_info = "Total parsed articles: " + str(len(articles))
        log_info += "\n" + "Total approved articles " + str(len(approved))
        log_info += (
            "\n" + "Total prepared articles " + str(len(prepared)))
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)

        return approved, prepared

    def prepare_articles(self, articles):
        """
        Given a set of article objects,
        decide whether its related article should be set
        Based on at least two factors,
          If the article is an Insight type of article,
          If both an Insight and its matching research article is in the set of articles
        Some Insight articles may be removed too
        """

        prepared_articles = []

        # Get a list of article DOIs for comparison later
        article_non_insight_doi_list = []
        article_insight_doi_list = []
        for article in articles:
            if article.article_type == "article-commentary":
                article_insight_doi_list.append(article.doi)
            else:
                article_non_insight_doi_list.append(article.doi)

        self.logger.info("Non-insight " + json.dumps(article_non_insight_doi_list))
        self.logger.info("Insight " + json.dumps(article_insight_doi_list))

        remove_article_doi = []

        # Process or delete articles as required
        for article in articles:
            self.logger.info(article.doi + " is type " + article.article_type)
            if article.article_type == "article-commentary":
                # Insight

                # Set the related article only if its related article is
                #  NOT in the list of articles DOIs
                # This means it is an insight for a VOR that was published previously
                related_article_doi = article.get_article_related_insight_doi()
                if related_article_doi in article_non_insight_doi_list:

                    self.logger.info("Article match on " + article.doi)

                    # We do not want to send for this insight
                    remove_article_doi.append(article.doi)
                    # We also do not want to leave it in the outbox, add it to the removal list
                    self.insight_articles_to_remove_from_outbox.append(article)

                    # We do want to set the related article for its match
                    for research_article in articles:
                        if research_article.doi == related_article_doi:
                            log_info = ("Setting match on " + related_article_doi +
                                        " to " + article.doi)
                            self.admin_email_content += "\n" + log_info
                            self.logger.info(log_info)
                            research_article.set_related_insight_article(article)

                else:
                    # Set this insights related article

                    self.logger.info("No article match on " + article.doi)

                    related_article_doi = article.get_article_related_insight_doi()
                    if related_article_doi:
                        related_article = get_related_article(
                            self.settings, self.get_tmp_dir(), related_article_doi,
                            self.related_articles, self.logger, self.admin_email_content)
                        if related_article:
                            article.set_related_insight_article(related_article)
                        else:
                            # Could not find the related article
                            log_info = ("Could not build the article related to insight " +
                                        article.doi)
                            self.admin_email_content += "\n" + log_info
                            self.logger.info(log_info)
                            remove_article_doi.append(article.doi)

        # Can remove articles now if required
        for article in articles:
            if article.doi not in remove_article_doi:
                prepared_articles.append(article)

        return prepared_articles

    def download_files_from_s3_outbox(self):
        """
        From the outbox folder in the S3 bucket,
        download the .xml to be processed
        """
        filenames = []
        bucket_name = self.publish_bucket

        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + self.outbox_folder
        files_in_bucket = storage.list_resources(orig_resource)

        for name in files_in_bucket:
            # Download objects from S3 and save to disk
            # Only need to copy .xml files
            if not re.search(".*\\.xml$", name):
                continue
            filename = name.split("/")[-1]
            dirname = self.get_tmp_dir()
            if dirname:
                filename_plus_path = dirname + os.sep + filename
                with open(filename_plus_path, 'wb') as open_file:
                    storage_resource_origin = orig_resource + name
                    storage.get_resource_to_file(storage_resource_origin, open_file)
                filenames.append(filename_plus_path)
        return filenames

    def parse_article_xml(self, article_xml_filenames):
        """
        Given a list of article XML filenames,
        parse the files and add the article object to our article map
        """

        articles = []

        for article_xml_filename in article_xml_filenames:

            article = articlelib.create_article(self.settings, self.get_tmp_dir)
            article.parse_article_file(article_xml_filename)
            article.pdf_cover_link = article.get_pdf_cover_page(
                article.doi_id, self.settings, self.logger)
            log_info = "Parsed " + article.doi_url
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            # Add article object to the object list
            articles.append(article)

            # Add article to the DOI to file name map
            self.xml_file_to_doi_map[article.doi] = article_xml_filename

        return articles

    def download_templates(self):
        """
        Download the email templates from s3
        """

        # Prepare email templates
        self.templates.download_email_templates_from_s3()
        if self.templates.email_templates_warmed is not True:
            log_info = 'PublicationEmail email templates did not warm successfully'
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            # Stop now! Return False if we do not have the necessary files
            return False
        else:
            log_info = 'PublicationEmail email templates warmed'
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            return True

    def approve_articles(self, articles):
        """
        Given a list of article objects, approve them for processing
        """

        approved_articles = []

        # Keep track of which articles to remove at the end
        remove_article_doi = []

        for article in articles:
            # Remove based on article type
            if article.article_type in ARTICLE_TYPES_DO_NOT_SEND:
                log_info = "Removing based on article type " + article.doi
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
                remove_article_doi.append(article.doi)

        # Can remove the articles now without affecting the loops using del
        for article in articles:
            if article.doi not in remove_article_doi:
                # Set whether the DOI was ever POA
                article.was_ever_poa = lax_provider.was_ever_poa(article.doi_id, self.settings)
                approved_articles.append(article)

        return approved_articles

    def send_emails_for_articles(self, articles):
        """given a list of articles, choose template, recipients, and send the email"""
        for article in articles:

            # Determine which email type or template to send
            email_type = choose_email_type(
                article_type=article.article_type,
                is_poa=article.is_poa,
                was_ever_poa=article.was_ever_poa,
                feature_article=is_feature_article(article)
                )

            # Get the authors depending on the article type
            if article.article_type == "article-commentary":
                # Check if the related article object was instantiated properly
                if hasattr(article.related_insight_article, "doi_id"):
                    authors = self.get_authors(article.related_insight_article.doi_id)
                else:
                    authors = None
                    self.log_cannot_find_authors(article.doi)
            else:
                authors = self.get_authors(article.doi_id)

            # Send an email to each author
            recipient_authors = choose_recipient_authors(
                authors=authors,
                article_type=article.article_type,
                feature_article=is_feature_article(article),
                related_insight_article=article.related_insight_article,
                features_email=self.settings.features_publication_recipient_email)

            if not recipient_authors:
                self.log_cannot_find_authors(article.doi)
            else:
                # Good, we can send emails
                for recipient_author in recipient_authors:
                    result = self.send_email(
                        email_type, article.doi_id, recipient_author, article, authors)
                    if result is False:
                        self.log_cannot_find_authors(article.doi)

    def send_email(self, email_type, elife_id, author, article, authors):
        """
        Given the email type and author,
        send the email
        """

        if author is None:
            return False
        if not author.get('e_mail') or str(author.get('e_mail')).strip() == "":
            return False

        # First process the headers
        try:
            headers = self.templates.get_email_headers(
                email_type=email_type,
                author=author,
                article=article,
                format="html")
        except:
            headers = None

        if not headers:
            log_info = (
                'Failed to load email headers for: doi_id: %s email_type: %s recipient_email: %s' %
                (str(elife_id), str(email_type), str(author.e_mail)))
            self.admin_email_content += "\n" + log_info
            return False

        try:
            # Now we can actually queue the email to be sent

            # Queue the email
            log_info = ("Sending " + email_type + " type email" +
                        " for article " + str(elife_id) +
                        " to recipient_email " + str(author.e_mail))
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)

            self.send_author_email(
                email_type=email_type,
                author=author,
                headers=headers,
                article=article,
                authors=authors,
                doi_id=elife_id,
                subtype="html")

            return True
        except Exception:
            self.logger.exception("An error has occurred on send_email method")

    def send_author_email(self, email_type, author, headers, article, authors, doi_id,
                          subtype="html"):
        """
        Format the email body and send the email by SMTP
        Only call this to send actual emails!
        """
        body = self.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article,
            authors=authors,
            format=subtype)

        message = email_provider.simple_message(
            headers["sender_email"], author.e_mail, headers["subject"], body,
            subtype=headers["format"], logger=self.logger)

        email_provider.smtp_send_messages(
            self.settings, messages=[message], logger=self.logger)
        self.logger.info('Email sending details: article %s, email %s, to %s' %
                         (doi_id, headers["email_type"], author.e_mail))

        return True

    def clean_outbox(self, prepared):
        """
        Clean out the S3 outbox folder
        """

        to_folder = get_to_folder_name(self.published_folder)

        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket

        # Compile a list of the published file names
        s3_key_names = []
        remove_doi_list = []
        processed_file_names = []
        for article in prepared:
            if article.doi not in self.articles_do_not_remove_from_outbox:
                remove_doi_list.append(article.doi)

        for article in self.insight_articles_to_remove_from_outbox:
            remove_doi_list.append(article.doi)

        for key, value in self.xml_file_to_doi_map.items():
            if key in remove_doi_list:
                processed_file_names.append(value)

        for name in processed_file_names:
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

            orig_resource = storage_provider + bucket_name + "/" + s3_key_name
            dest_resource = storage_provider + bucket_name + "/" + new_s3_key_name

            # First copy
            storage.copy_resource(orig_resource, dest_resource)

            # Then delete the old key if successful
            storage.delete_resource(orig_resource)

    def get_authors(self, doi_id=None, corresponding=None, local_document=None):
        """
        Using the EJP data provider, get the column headings
        and author data, and reassemble into a list of authors
        document is only provided when running tests, otherwise just specify the doi_id
        """
        author_list = []
        # EJP data provider
        ejp_object = ejp.EJP(self.settings, self.get_tmp_dir())

        (column_headings, authors) = ejp_object.get_authors(
            doi_id=doi_id, corresponding=corresponding, local_document=local_document)

        # Authors will be none if there is not data
        if authors is None:
            log_info = "No authors found for article doi id " + str(doi_id)
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            return None

        for author in authors:
            i = 0
            recipient_author = {}
            for value in author:
                heading = column_headings[i]
                recipient_author[heading] = value
                i = i + 1
            # Special: convert the dict to an object for use in templates
            author_list.append(recipient_author)

        return author_list

    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """

        # Note: Create a verified sender email address, only done once
        # conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()

        body = self.get_admin_email_body(current_time)
        subject = self.get_admin_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if isinstance(self.settings.ses_admin_email, list):
            for email in self.settings.ses_admin_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_admin_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger)

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger)
            self.logger.info('Email sending details: admin email, email %s, to %s' %
                             ("PublicationEmail", email))

        return True

    def get_admin_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = get_activity_status_text(self.activity_status)

        subject = (self.name + " " + activity_status_text +
                   ", " + datetime_string +
                   ", eLife SWF domain: " + self.settings.domain)

        return subject

    def get_admin_email_body(self, current_time):
        """
        Format the body of the email
        """

        body = ""

        date_format = '%Y-%m-%dT%H:%M:%S.000Z'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = get_activity_status_text(self.activity_status)

        # Bulk of body
        body += self.name + " status:" + "\n"
        body += "\n"
        body += activity_status_text + "\n"
        body += "\n"
        body += "Details:" + "\n"
        body += "\n"
        body += self.admin_email_content + "\n"
        body += "\n"

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


def get_related_article(settings, tmp_dir, doi, related_articles, logger, admin_email_content):
    """
    When populating related articles, given a DOI,
    download the article XML and parse it,
    return a previously parsed article object if it exists
    """

    article = None

    for article in related_articles:
        if article.doi == doi:
            # Return an existing article object
            log_info = "Hit the article cache on " + doi
            admin_email_content += "\n" + log_info
            logger.info(log_info)
            return article

    # Article for this DOI does not exist, populate it
    doi_id = utils.msid_from_doi(doi)
    article = articlelib.create_article(settings, tmp_dir, doi_id)

    if not article:
        log_info = "Could not build the related article " + doi
        admin_email_content += "\n" + log_info
        logger.info(log_info)
        return article

    related_articles.append(article)

    log_info = "Building article for " + doi
    admin_email_content += "\n" + log_info
    logger.info(log_info)

    return article


def get_to_folder_name(published_folder):
    """
    From the date_stamp
    return the S3 folder name to save published files into
    """
    to_folder = None

    date_folder_name = set_datestamp()
    to_folder = published_folder + date_folder_name + "/"

    return to_folder


def choose_recipient_authors(authors, article_type, feature_article,
                             related_insight_article, features_email):
    """
    The recipients of the email will change depending on if it is a
    feature article
    """
    recipient_authors = []
    if (feature_article is True
            or article_type == "article-commentary"
            or related_insight_article is not None):
        # feature article recipients

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if isinstance(features_email, list):
            for email in features_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(features_email)

        for recipient_email in recipient_email_list:
            feature_author = {}
            feature_author["first_nm"] = "Features"
            feature_author["e_mail"] = recipient_email
            recipient_authors.append(feature_author)

    if authors and len(recipient_authors) > 0:
        recipient_authors = recipient_authors + authors
    elif authors:
        recipient_authors = authors

    return recipient_authors


def set_datestamp():
    arrow_date = arrow.utcnow()
    date_stamp = (
        str(arrow_date.datetime.year) + str(arrow_date.datetime.month).zfill(2) +
        str(arrow_date.datetime.day).zfill(2))
    return date_stamp


def is_feature_article(article):
    if (article.is_in_display_channel("Feature article") is True or
            article.is_in_display_channel("Feature Article") is True):
        return True
    return False


def choose_email_type(article_type, is_poa, was_ever_poa, feature_article):
    """
    Given some article details, we can choose the
    appropriate email template
    """
    email_type = None

    if article_type == "article-commentary":
        # Insight
        email_type = "author_publication_email_Insight_to_VOR"

    elif article_type == "discussion" and feature_article is True:
        # Feature article
        email_type = "author_publication_email_Feature"

    elif article_type == "research-article":
        if is_poa is True:
            # POA article
            email_type = "author_publication_email_POA"

        elif is_poa is False:
            # VOR article, decide based on if it was ever POA
            if was_ever_poa is True:
                email_type = "author_publication_email_VOR_after_POA"

            else:
                # False or None is allowed here
                email_type = "author_publication_email_VOR_no_POA"

    return email_type


def get_activity_status_text(activity_status):
    """
    Given the activity status boolean, return a human
    readable text version
    """
    if activity_status is True:
        activity_status_text = "Success!"
    else:
        activity_status_text = "FAILED."

    return activity_status_text
