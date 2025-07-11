import json
import time
import os
import glob
import smtplib
from collections import OrderedDict
from provider import (
    ejp,
    email_provider,
    lax_provider,
    outbox_provider,
    pdf_cover_page,
    preprint,
    templates,
    utils,
    yaml_provider,
)
import provider.article as articlelib
from activity.objects import Activity


# maximum emails to send per second
MAX_EMAILS_PER_SECOND = 1
# time in seconds to sleep when an smtplib.SMTPDataError exception is raised
SLEEP_SECONDS = 5
# number of times to sleep after reaching a sending exception
SENDING_RETRY = 3


FEATURES_RECIPIENT_NAME_DEFAULT = "Features"


class EmailRecipientException(RuntimeError):
    "exception to raise if an email recipient is incomplete"


class EmailTemplateException(RuntimeError):
    "exception to raise if an email template cannot be rendered"


class EmailSendException(RuntimeError):
    "exception to raise if sending an email cannot be completed"


class EmailRulesException(RuntimeError):
    "exception to raise if something in the email rules is a problem"


class activity_PublicationEmail(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PublicationEmail, self).__init__(
            settings, logger, client, token, activity_task
        )

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
        self.outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder(self.name)
        )
        self.published_folder = outbox_provider.published_folder(
            self.s3_bucket_folder(self.name)
        )
        self.not_published_folder = outbox_provider.not_published_folder(
            self.s3_bucket_folder(self.name)
        )

        # Track XML files selected for publication
        self.insight_articles_to_remove_from_outbox = []
        self.articles_do_not_remove_from_outbox = []

        self.admin_email_content = ""

    def do_activity(self, data=None):
        """
        PublicationEmail activity, do the work
        """

        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

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
            outbox_s3_key_names = outbox_provider.get_outbox_s3_key_names(
                self.settings, self.publish_bucket, self.outbox_folder
            )
            outbox_provider.download_files_from_s3_outbox(
                self.settings,
                self.publish_bucket,
                outbox_s3_key_names,
                self.get_tmp_dir(),
                self.logger,
            )
            article_xml_filenames = glob.glob(self.get_tmp_dir() + "/*.xml")
        except Exception:
            self.logger.exception("Failed to download files from the S3 outbox")
            return self.ACTIVITY_PERMANENT_FAILURE

        rules = yaml_provider.load_config(
            self.settings, config_type="publication_email"
        )

        try:
            (
                approved,
                prepared,
                not_published_articles,
                xml_file_to_doi_map,
            ) = self.process_articles(article_xml_filenames, rules)
        except Exception:
            self.logger.exception(
                "Failed to parse, approve, and prepare all the articles"
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # return now if no articles are approved and prepared
        if not prepared and not not_published_articles:
            self.logger.info("No articles were approved and prepared for sending")
            self.send_admin_email(True)
            return True

        try:
            self.send_and_clean(
                prepared, not_published_articles, xml_file_to_doi_map, rules
            )
        except Exception:
            self.logger.exception("An error occurred on do_activity method.")

        return True

    def send_and_clean(
        self, prepared, not_published_articles, xml_file_to_doi_map, rules
    ):
        "send the emails, clean the outbox, send the admin email"
        self.send_emails_for_articles(prepared, rules)
        self.clean_outbox(prepared, not_published_articles, xml_file_to_doi_map)
        # Send email to admins with the status
        self.send_admin_email(True)

    def clean_outbox(self, prepared, not_published_articles, xml_file_to_doi_map):
        "clean the S3 outbox of files"
        # Clean the outbox
        published_file_names = s3_key_names_to_clean(
            self.outbox_folder,
            prepared,
            xml_file_to_doi_map,
            self.articles_do_not_remove_from_outbox,
            self.insight_articles_to_remove_from_outbox,
        )
        date_stamp = utils.set_datestamp()
        to_folder = outbox_provider.get_to_folder_name(
            self.published_folder, date_stamp
        )
        # clean published files from the outbox
        outbox_provider.clean_outbox(
            self.settings,
            self.publish_bucket,
            self.outbox_folder,
            to_folder,
            published_file_names,
        )

        # clean not_published files from the outbox
        not_published_file_names = s3_key_names_to_clean(
            self.outbox_folder,
            not_published_articles,
            xml_file_to_doi_map,
            self.articles_do_not_remove_from_outbox,
            [],
        )
        not_published_to_folder = outbox_provider.get_to_folder_name(
            self.not_published_folder, date_stamp
        )
        outbox_provider.clean_outbox(
            self.settings,
            self.publish_bucket,
            self.outbox_folder,
            not_published_to_folder,
            not_published_file_names,
        )

    def log_cannot_find_authors(self, doi):
        log_info = (
            "Leaving article in the outbox because we cannot "
            + "find its authors: "
            + doi
        )
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
        # Make a note of this and we will not remove from the outbox, save for a later day
        self.articles_do_not_remove_from_outbox.append(doi)

    def process_articles(self, article_xml_filenames, rules):
        """multi-step parsing, approving, and preparing of article files"""
        articles, xml_file_to_doi_map = self.parse_article_xml(article_xml_filenames)
        approved, not_published_articles = self.approve_articles(articles, rules)
        prepared = self.prepare_articles(approved, rules)

        log_info = "Total parsed articles: " + str(len(articles))
        log_info += "\n" + "Total approved articles: " + str(len(approved))
        log_info += "\n" + "Total prepared articles: " + str(len(prepared))
        log_info += (
            "\n" + "Total not published articles: " + str(len(not_published_articles))
        )
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)

        return approved, prepared, not_published_articles, xml_file_to_doi_map

    def prepare_articles(self, articles, rules):
        """
        Given a set of article objects,
        decide whether its related article should be set
        Based on at least two factors,
          If the article is an Insight type of article,
          If both an Insight and its matching research article is in the set of articles
        Some Insight articles may be removed too
        """

        prepared_articles = []

        article_non_insight_doi_list = get_non_insight_doi_list(articles, self.logger)

        remove_article_doi = []
        related_articles = []

        # Process or delete articles as required
        for article in articles:
            use_article_type = getattr(article, "article_type")
            # detect preprint articles
            if preprint.is_article_preprint(article):
                use_article_type = "preprint"

            self.logger.info(article.doi + " is type " + use_article_type)
            if is_insight_article(article):
                self.set_related_article(
                    article,
                    articles,
                    related_articles,
                    article_non_insight_doi_list,
                    remove_article_doi,
                )

        # Can remove articles now if required
        for article in articles:
            use_article_type = getattr(article, "article_type")
            # detect preprint articles
            if preprint.is_article_preprint(article):
                use_article_type = "preprint"

            if article.doi not in remove_article_doi:
                # check if an email_type can be found in the rules
                try:
                    email_type = choose_email_type(
                        article_type=use_article_type,
                        is_poa=article.is_poa,
                        was_ever_poa=article.was_ever_poa,
                        rules=rules,
                        version_doi=getattr(article, "version_doi", None),
                    )
                except EmailRulesException as exception:
                    self.logger.info(str(exception))
                    continue

                self.logger.info(
                    (
                        "%s, got email_type: %s for DOI: %s, "
                        "article_type: %s, is_poa: %s, was_ever_poa: %s, version_doi: %s"
                    )
                    % (
                        self.name,
                        email_type,
                        article.doi,
                        use_article_type,
                        article.is_poa,
                        article.was_ever_poa,
                        getattr(article, "version_doi", None),
                    )
                )

                prepared_articles.append(article)

        return prepared_articles

    def set_related_article(
        self,
        article,
        articles,
        related_articles,
        article_non_insight_doi_list,
        remove_article_doi,
    ):
        """set the related article for an insight article"""
        was_set = set_related_article_internal(
            article,
            articles,
            article_non_insight_doi_list,
            self.logger,
            self.admin_email_content,
        )
        if was_set:
            # remove this insight from the list to send
            remove_article_doi.append(article.doi)
            # We also do not want to leave it in the outbox, add it to the removal list
            self.insight_articles_to_remove_from_outbox.append(article)
        else:
            # If related article not set from internal sources, set from external source
            self.logger.info("No internal article match on " + article.doi)
            was_set = set_related_article_external(
                self.settings,
                self.get_tmp_dir(),
                article,
                related_articles,
                self.logger,
                self.admin_email_content,
            )
        # finally if we count not set the value
        if not was_set:
            log_info = "Could not build the article related to insight " + article.doi
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            remove_article_doi.append(article.doi)

    def parse_article_xml(self, article_xml_filenames):
        """
        Given a list of article XML filenames,
        parse the files and add the article object to our article map
        """

        articles = []
        xml_file_to_doi_map = {}

        for article_xml_filename in article_xml_filenames:
            article = articlelib.create_article(self.settings, self.get_tmp_dir)
            article.parse_article_file(article_xml_filename)
            article.pdf_cover_link = pdf_cover_page.get_pdf_cover_page(
                article.doi_id, self.settings, self.logger
            )
            log_info = "Parsed " + article.doi_url
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            # Add article object to the object list
            articles.append(article)

            # Add article to the DOI to file name map
            xml_file_to_doi_map[article.doi] = article_xml_filename

        return articles, xml_file_to_doi_map

    def download_templates(self):
        """
        Download the email templates
        """

        # Prepare email templates
        self.templates.copy_email_templates(self.settings.email_templates_path)
        if self.templates.email_templates_warmed is not True:
            log_info = "PublicationEmail email templates did not warm successfully"
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
            # Stop now! Return False if we do not have the necessary files
            return False

        log_info = "PublicationEmail email templates warmed"
        self.admin_email_content += "\n" + log_info
        self.logger.info(log_info)
        return True

    def approve_articles(self, articles, rules):
        """
        Given a list of article objects, approve them for processing
        """

        approved_articles = []

        # Keep track of which articles to remove at the end
        remove_article_doi = []
        not_published_articles = []

        for article in articles:
            use_article_type = getattr(article, "article_type")
            # detect preprint articles
            if preprint.is_article_preprint(article):
                use_article_type = "preprint"

            # Remove based on article type
            if use_article_type in do_not_send_article_types_from_rules(rules):
                log_info = "Removing based on article type " + article.doi
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
                not_published_articles.append(article)
                remove_article_doi.append(article.doi)

        # Can remove the articles now without affecting the loops using del
        for article in articles:
            if article.doi not in remove_article_doi:
                # Set whether the DOI was ever POA
                article.was_ever_poa = lax_provider.was_ever_poa(
                    article.doi_id, self.settings
                )
                approved_articles.append(article)

        return approved_articles, not_published_articles

    def send_emails_for_articles(self, articles, rules):
        """given a list of articles, choose template, recipients, and send the email"""
        for article in articles:
            # Determine which email type or template to send

            use_article_type = getattr(article, "article_type")
            # detect preprint articles
            if preprint.is_article_preprint(article):
                use_article_type = "preprint"

            # use the rules for choosing the email template
            email_type = choose_email_type(
                article_type=use_article_type,
                is_poa=article.is_poa,
                was_ever_poa=article.was_ever_poa,
                rules=rules,
                version_doi=getattr(article, "version_doi", None),
            )

            # Get the article author data
            authors = self.article_authors_by_article_type(article)

            # process the recipient data, adding Feature article recipients if applicable
            recipient_authors = choose_recipient_authors(
                authors=authors,
                article_type=use_article_type,
                feature_article=is_feature_article(article),
                related_insight_article=article.related_insight_article,
                features_email=self.settings.features_publication_recipient_email,
                rules=rules,
            )

            if not recipient_authors:
                self.log_cannot_find_authors(article.doi)
            else:
                # Good, we can send emails
                for recipient_author in recipient_authors:
                    try:
                        self.send_email(
                            email_type,
                            article.doi_id,
                            recipient_author,
                            article,
                            authors,
                            self.settings.ses_bcc_recipient_email,
                        )
                    except Exception:
                        log_info = (
                            "Failed to send email for article %s to recipient %s"
                            % (article.doi, recipient_author)
                        )
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)

    def article_authors_by_article_type(self, article):
        """get article authors depending on the article type"""
        authors = None
        doi_id = None
        source_article = None
        if is_insight_article(article) and hasattr(
            article.related_insight_article, "doi_id"
        ):
            # use related article to populate authors
            doi_id = article.related_insight_article.doi_id
            source_article = article.related_insight_article
        else:
            # use the actual article to populate authors
            doi_id = article.doi_id
            source_article = article

        if doi_id and source_article:
            authors = self.article_authors(doi_id, source_article)

        return authors

    def article_authors(self, doi_id, article):
        """get a merged list of authors from CSV for the doi_id and from the article object"""
        article_type = None
        version = None
        if hasattr(article, "article_type"):
            article_type = article.article_type
        # determine if XML is for a preprint
        if preprint.is_article_preprint(article):
            # get version from version DOI
            version = utils.version_doi_parts(article.version_doi)[1]
            article_type = "preprint"
        article_authors = self.get_authors(doi_id, article_type, version)
        # do not get email addresses from the XML for feature articles
        if is_feature_article(article):
            xml_authors = []
        else:
            xml_authors = authors_from_xml(article)

        all_authors = self.merge_recipients(article_authors, xml_authors)
        return all_authors

    def merge_recipients(self, list_one, list_two):
        """merge two lists of email recipients with no deuplicate email addresses"""
        merged_list = []

        list_one_email_list = []
        if list_one:
            merged_list = list_one
            list_one_email_list = [recipient.get("e_mail") for recipient in list_one]

        if list_two:
            # add values from list_two to list_one
            for recipient in list_two:
                if (
                    recipient.get("e_mail")
                    and recipient.get("e_mail") not in list_one_email_list
                ):
                    self.admin_email_content += (
                        "\nAdding %s from additional recipient list"
                        % recipient.get("e_mail")
                    )
                    merged_list.append(recipient)

        return merged_list

    def send_email(self, email_type, elife_id, author, article, authors, bcc=None):
        """
        Given the email type and author,
        send the email
        """

        if author is None:
            log_message = "author is None"
            self.logger.exception(log_message)
            raise EmailRecipientException(log_message)
        if not author.get("e_mail") or str(author.get("e_mail")).strip() == "":
            log_message = "author has no e_mail"
            self.logger.exception(log_message)
            raise EmailRecipientException(log_message)

        # First process the headers
        try:
            headers = self.templates.get_email_headers(
                email_type=email_type, author=author, article=article, format="html"
            )
        except Exception as exception:
            log_message = (
                "Failed to load email headers for: doi_id: %s email_type: %s recipient_email: %s"
                % (str(elife_id), str(email_type), str(author.get("e_mail")))
            )
            self.admin_email_content += "\n" + log_message
            self.logger.exception(log_message)
            raise EmailTemplateException(log_message) from exception

        try:
            # Now we can actually queue the email to be sent

            # Queue the email
            log_info = (
                "Sending "
                + email_type
                + " type email"
                + " for article "
                + str(elife_id)
                + " to recipient_email "
                + str(author.get("e_mail"))
            )
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)

            self.send_author_email(
                email_type=email_type,
                author=author,
                headers=headers,
                article=article,
                authors=authors,
                doi_id=elife_id,
                subtype="html",
                bcc=bcc,
            )

        except Exception as exception:
            log_message = "An error has occurred on send_email method"
            self.logger.exception(log_message)
            raise EmailSendException(log_message) from exception

    def send_author_email(
        self,
        email_type,
        author,
        headers,
        article,
        authors,
        doi_id,
        subtype="html",
        bcc=None,
    ):
        """
        Format the email body and send the email by SMTP
        Only call this to send actual emails!
        """
        body = self.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article,
            authors=authors,
            format=subtype,
        )

        message = email_provider.simple_message(
            headers["sender_email"],
            str(author.get("e_mail")),
            headers["subject"],
            body,
            subtype=headers["format"],
            logger=self.logger,
        )

        connection = email_provider.smtp_connect(self.settings, self.logger)

        result = None
        tries = 0
        while tries < SENDING_RETRY:
            try:
                result = email_provider.smtp_send_message(
                    connection, message, logger=self.logger, bcc=bcc
                )
                break
            except smtplib.SMTPDataError as exception:
                self.logger.exception(
                    (
                        "Sending by SMTP reached smtplib.SMTPDataError, "
                        "will sleep %s seconds and then try again: %s"
                    )
                    % (SLEEP_SECONDS, str(exception))
                )
                # sleep a short time
                time.sleep(SLEEP_SECONDS)
            finally:
                tries += 1

        self.logger.info(
            "Email sending details: result %s, tries %s, article %s, email %s, to %s"
            % (result, tries, doi_id, headers["email_type"], str(author.get("e_mail")))
        )

        # sleep to not exceed max emails per second sending rate
        if MAX_EMAILS_PER_SECOND and MAX_EMAILS_PER_SECOND > 0:
            time.sleep(1 / MAX_EMAILS_PER_SECOND)

        return True

    def get_authors(self, doi_id=None, article_type=None, version=None):
        """
        Using the EJP data provider, get the column headings
        and author data, and reassemble into a list of authors
        for the article with doi_id
        """

        # EJP data provider
        ejp_object = ejp.EJP(self.settings, self.get_tmp_dir())

        if article_type == "preprint":
            # get preprint authors
            (column_headings, authors) = ejp_object.get_preprint_authors(
                doi_id=doi_id, version=version
            )
        else:
            (column_headings, authors) = ejp_object.get_authors(doi_id=doi_id)
        return self.get_author_list(column_headings, authors, doi_id)

    def get_author_list(self, column_headings, authors, doi_id):
        author_list = []
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
                try:
                    heading = column_headings[i]
                except IndexError:
                    log_info = "Missing column_headings for article doi id " + str(
                        doi_id
                    )
                    continue
                recipient_author[heading] = value
                i = i + 1
            # Special: convert the dict to an object for use in templates
            author_list.append(recipient_author)

        return author_list

    def send_admin_email(self, activity_status):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """

        # Note: Create a verified sender email address, only done once
        # conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()
        date_format = "%Y-%m-%d %H:%M"
        datetime_string = time.strftime(date_format, current_time)
        activity_status_text = utils.get_activity_status_text(activity_status)

        body = email_provider.get_email_body_head(self.name, activity_status_text, {})
        body += "\nDetails:\n\n%s\n" % self.admin_email_content
        body += email_provider.get_admin_email_body_foot(
            self.get_activityId(),
            self.get_workflowId(),
            datetime_string,
            self.settings.domain,
        )
        subject = email_provider.get_email_subject(
            datetime_string, activity_status_text, self.name, self.settings.domain, None
        )
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
                sender_email, email, subject, body, logger=self.logger
            )

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger
            )
            self.logger.info(
                "Email sending details: admin email, email %s, to %s"
                % ("PublicationEmail", email)
            )

        return True


def is_insight_article(article):
    """is an article object an insight article"""
    if (
        hasattr(article, "article_type")
        and article.article_type == "article-commentary"
    ):
        return True
    return False


def get_non_insight_doi_list(articles, logger):
    """get a list of non-insight articles"""
    # Get a list of article DOIs for comparison later
    article_non_insight_doi_list = []
    article_insight_doi_list = []
    for article in articles:
        if is_insight_article(article):
            article_insight_doi_list.append(article.doi)
        else:
            article_non_insight_doi_list.append(article.doi)

    logger.info("Non-insight " + json.dumps(article_non_insight_doi_list))
    logger.info("Insight " + json.dumps(article_insight_doi_list))

    return article_non_insight_doi_list


def set_related_article_internal(
    article, articles, non_insight_doi_list, logger, admin_email_content
):
    """for insight article, set the related_article property from an article in the outbox"""
    # Set the related article of an insight article only if its related research article is
    #  in the list of non_insight_doi_list (from the outbox)
    related_article_doi = article.get_article_related_insight_doi()
    if related_article_doi in non_insight_doi_list:
        logger.info("Article match on " + article.doi)

        # Set the relation on the research article to its insight article
        for research_article in articles:
            if research_article.doi == related_article_doi:
                log_info = (
                    "Setting match on " + related_article_doi + " to " + article.doi
                )
                admin_email_content += "\n" + log_info
                logger.info(log_info)
                research_article.set_related_insight_article(article)
                # return True so we can ignore this insight article from sending
                return True
    return None


def set_related_article_external(
    settings, tmp_dir, article, related_articles, logger, admin_email_content
):
    """for insight article, set the related_article property getting it from the big bucket"""
    related_article_doi = article.get_article_related_insight_doi()
    if related_article_doi:
        related_article = get_related_article(
            settings,
            tmp_dir,
            related_article_doi,
            related_articles,
            logger,
            admin_email_content,
        )
        if related_article:
            article.set_related_insight_article(related_article)
            return True
    return None


def s3_key_names_to_clean(
    outbox_folder, prepared, xml_file_to_doi_map, do_not_remove, do_remove
):
    """compile a list of S3 key names to clean from the outbox folder"""

    # Compile a list of the published file names
    s3_key_names = []
    remove_doi_list = []
    processed_file_names = []
    for article in prepared:
        if article and article.doi not in do_not_remove:
            remove_doi_list.append(article.doi)

    for article in do_remove:
        remove_doi_list.append(article.doi)

    if xml_file_to_doi_map:
        for key, value in list(xml_file_to_doi_map.items()):
            if key in remove_doi_list:
                processed_file_names.append(value)

    for name in processed_file_names:
        filename = name.split(os.sep)[-1]
        s3_key_name = outbox_folder + filename
        s3_key_names.append(s3_key_name)

    return s3_key_names


def get_related_article(
    settings, tmp_dir, doi, related_articles, logger, admin_email_content
):
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


def choose_recipient_authors(
    authors,
    article_type,
    feature_article,
    related_insight_article,
    features_email,
    rules,
):
    """
    The recipients of the email will change depending on if it is a
    feature article
    """
    recipient_authors = []

    recipient_types = recipients_from_rules(rules, article_type)
    features_recipient_name = features_recipient_name_from_rules(rules, article_type)
    if (
        feature_article is True
        or related_insight_article is not None
        or "features_publication_recipient_email" in recipient_types
    ):
        recipient_email_list = []
        # Handle multiple recipients, if specified
        if isinstance(features_email, list):
            for email in features_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(features_email)

        for recipient_email in recipient_email_list:
            feature_author = {}
            feature_author["first_nm"] = features_recipient_name
            feature_author["e_mail"] = recipient_email
            recipient_authors.append(feature_author)

    if authors and recipient_authors:
        recipient_authors = recipient_authors + authors
    elif authors:
        recipient_authors = authors

    return recipient_authors


def is_feature_article(article):
    if (
        article.is_in_display_channel("Feature article") is True
        or article.is_in_display_channel("Feature Article") is True
    ):
        return True
    return False


def choose_email_type(
    article_type,
    is_poa,
    was_ever_poa,
    rules,
    version_doi=None,
):
    """
    Given some article details, we can choose the
    appropriate email template
    """
    if version_doi:
        # get version from version DOI
        version = utils.version_doi_parts(version_doi)[1]
    else:
        version = None

    return email_type_from_rules(
        rules,
        article_type,
        is_poa=is_poa,
        was_ever_poa=was_ever_poa,
        version=version,
    )


def author_data(email, surname, given_names):
    return OrderedDict(
        [
            ("e_mail", email),
            ("first_nm", str(given_names)),
            ("last_nm", str(surname)),
        ]
    )


def authors_from_xml(article):
    """get corresponding email addresses from the article XML"""
    authors = []
    for author in [author for author in article.authors if author.get("corresp")]:
        # find the email from two possible places
        if author.get("email"):
            # email value is a list of email addresses
            for email in author.get("email"):
                authors.append(
                    author_data(email, author.get("surname"), author.get("given-names"))
                )
        elif author.get("affiliations"):
            # add author for each affiliation email
            for aff in author.get("affiliations"):
                if aff.get("email"):
                    authors.append(
                        author_data(
                            aff.get("email"),
                            author.get("surname"),
                            author.get("given-names"),
                        )
                    )
    return authors


def email_type_from_rules(
    rules, article_type, is_poa=None, was_ever_poa=None, version=None
):
    "return email_type from rules which match the parameters"
    if not rules:
        return None
    for rule_name in rules:
        rule_data = rules.get(rule_name)
        if rule_data.get(
            "article_type"
        ) and article_type in yaml_provider.value_as_list(
            rule_data.get("article_type")
        ):
            try:
                assert isinstance(
                    rule_data.get("email_type"), str
                ), "`email_type` must be a string"
            except AssertionError as exception:
                raise EmailRulesException(
                    "email_type is not str in rule for article_type %s"
                    % rule_data.get("article_type")
                ) from exception
            # match criteria ordered from most restrictive to most lenient comparisons
            if (
                not is_poa
                and rule_data.get("article_status") == "vor"
                and was_ever_poa
                and rule_data.get("was_ever_poa") is True
            ):
                return rule_data.get("email_type")
            if (
                not is_poa
                and rule_data.get("article_status") == "vor"
                and not was_ever_poa
                and not rule_data.get("was_ever_poa")
            ):
                return rule_data.get("email_type")
            if is_poa and rule_data.get("article_status") == "poa":
                return rule_data.get("email_type")
            if version and rule_data.get("first_version") is not None:
                if int(version) <= 1 and rule_data.get("first_version") is True:
                    return rule_data.get("email_type")
                if int(version) > 1 and rule_data.get("first_version") is False:
                    return rule_data.get("email_type")
            if (
                not is_poa
                and not was_ever_poa
                and not rule_data.get("article_status")
                and not rule_data.get("first_version")
            ):
                return rule_data.get("email_type")
            if (
                is_poa is None
                and was_ever_poa is None
                and not rule_data.get("first_version")
            ):
                return rule_data.get("email_type")

    return None


def recipients_from_rules(rules, article_type):
    "get recipient types from the rules"
    recipient_types = []
    for rule_name in rules:
        rule_data = rules.get(rule_name)
        if article_type in yaml_provider.value_as_list(rule_data.get("article_type")):
            recipient_types = yaml_provider.value_as_list(rule_data.get("recipients"))
    return recipient_types


def features_recipient_name_from_rules(rules, article_type):
    "get recipient name for email sent to features team"
    features_recipient_name = FEATURES_RECIPIENT_NAME_DEFAULT
    for rule_name in rules:
        rule_data = rules.get(rule_name)
        if article_type in yaml_provider.value_as_list(rule_data.get("article_type")):
            if rule_data.get("features_recipient_name"):
                features_recipient_name = rule_data.get("features_recipient_name")
    return features_recipient_name


def do_not_send_article_types_from_rules(rules):
    "from YAML file rules return list of article_type where do_not_send is true"
    if not rules:
        return []
    article_types = set()
    for rule_name in rules:
        rule_data = rules.get(rule_name)
        if (
            rule_data.get("do_not_send")
            and rule_data.get("do_not_send") is True
            and rule_data.get("article_type")
        ):
            article_types = article_types.union(
                yaml_provider.value_as_list(rule_data.get("article_type"))
            )

    return sorted(list(article_types))
