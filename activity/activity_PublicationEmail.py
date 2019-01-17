import boto.swf
import json
import time
import os
import arrow
import requests
import boto.s3
from boto.s3.connection import S3Connection

import provider.simpleDB as dblib
import provider.templates as templatelib
import provider.ejp as ejplib
import provider.article as articlelib
import provider.s3lib as s3lib
import provider.blacklist as blacklist
import provider.lax_provider as lax_provider
from activity.objects import Activity

"""
PublicationEmail activity
"""

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

        # Data provider
        self.db = dblib.SimpleDB(settings)

        # Templates provider
        self.templates = templatelib.Templates(settings, self.get_tmp_dir())

        # EJP data provider
        self.ejp = ejplib.EJP(settings, self.get_tmp_dir())

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = "publication_email/outbox/"
        self.published_folder = "publication_email/published/"

        # Track the success of some steps
        self.activity_status = None

        # Track XML files selected for publication
        self.article_xml_filenames = []
        self.xml_file_to_doi_map = {}
        self.articles = []
        self.related_articles = []
        self.articles_approved = []
        self.articles_approved_prepared = []
        self.insight_articles_to_remove_from_outbox = []
        self.articles_do_not_remove_from_outbox = []

        # Default is do not send duplicate emails
        self.allow_duplicates = False

        # Article types for which not to send emails
        self.article_types_do_not_send = []
        self.article_types_do_not_send.append('editorial')
        self.article_types_do_not_send.append('correction')
        self.article_types_do_not_send.append('retraction')

        # Email types, for sending previews of each template
        self.email_types = []
        self.email_types.append('author_publication_email_POA')
        self.email_types.append('author_publication_email_VOR_after_POA')
        self.email_types.append('author_publication_email_VOR_no_POA')
        self.email_types.append('author_publication_email_Insight_to_VOR')
        self.email_types.append('author_publication_email_Feature')

        self.date_stamp = self.set_datestamp()

        self.admin_email_content = ''

    def do_activity(self, data=None):
        """
        PublicationEmail activity, do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Connect to DB
        db_conn = self.db.connect()

        # Check for whether the workflow execution was told to allow duplicate emails
        #  default is False
        try:
            self.allow_duplicates = data["data"]["allow_duplicates"]
        except KeyError:
            # Not specified? Ok, just use the default
            pass

        try:
            # Download templates
            templates_downloaded = self.download_templates()
            if templates_downloaded is True:

                # Download the article XML from S3 and parse them
                self.article_xml_filenames = self.download_files_from_s3_outbox()
                self.articles = self.parse_article_xml(self.article_xml_filenames)

                self.articles_approved = self.approve_articles(self.articles)

                self.articles_approved_prepared = self.prepare_articles(self.articles_approved)

                if self.logger:
                    log_info = "Total parsed articles: " + str(len(self.articles))
                    log_info += "\n" + "Total approved articles " + str(len(self.articles_approved))
                    log_info += ("\n" + "Total prepared articles " +
                                 str(len(self.articles_approved_prepared)))
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)

            # For the set of articles now select the template, authors and queue the emails
            for article in self.articles_approved_prepared:

                # Determine which email type or template to send
                email_type = self.choose_email_type(
                    article_type=article.article_type,
                    is_poa=article.is_poa,
                    was_ever_poa=article.was_ever_poa,
                    feature_article=self.is_feature_article(article)
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
                recipient_authors = self.choose_recipient_authors(
                    authors=authors,
                    article_type=article.article_type,
                    feature_article=self.is_feature_article(article),
                    related_insight_article=article.related_insight_article)

                if recipient_authors is None:
                    self.log_cannot_find_authors(article.doi)
                else:
                    # Good, we can send emails
                    for recipient_author in recipient_authors:
                        result = self.send_email(email_type, article.doi_id, recipient_author, article, authors)
                        if result is False:
                            self.log_cannot_find_authors(article.doi)


              # Temporary for testing, send a test run - LATER FOR TESTING TEMPLATES
              #self.send_email_testrun(self.email_types, article.doi_id, authors, article)

            # Clean the outbox
            self.clean_outbox()

            # Send email to admins with the status
            self.activity_status = True
            self.send_admin_email()

            return True
        except Exception:
            if self.logger:
                self.logger.exception("An error occured on do_activity method.")
                pass

    def log_cannot_find_authors(self, doi):
        if self.logger:
            log_info = ("Leaving article in the outbox because we cannot " +
                        "find its authors: " + doi)
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)
        # Make a note of this and we will not remove from the outbox, save for a later day
        self.articles_do_not_remove_from_outbox.append(doi)

    def set_datestamp(self):
        a = arrow.utcnow()
        date_stamp = (str(a.datetime.year) + str(a.datetime.month).zfill(2) +
                      str(a.datetime.day).zfill(2))
        return date_stamp

    def choose_email_type(self, article_type, is_poa, was_ever_poa, feature_article):
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

        #print "Non-insight " + json.dumps(article_non_insight_doi_list)
        #print "Insight " + json.dumps(article_insight_doi_list)

        remove_article_doi = []

        # Process or delete articles as required
        for article in articles:
            #print article.doi + " is type " + article.article_type
            if article.article_type == "article-commentary":
                # Insight

                # Set the related article only if its related article is
                #  NOT in the list of articles DOIs
                # This means it is an insight for a VOR that was published previously
                related_article_doi = article.get_article_related_insight_doi()
                if related_article_doi in article_non_insight_doi_list:

                    #print "Article match on " + article.doi

                    # We do not want to send for this insight
                    remove_article_doi.append(article.doi)
                    # We also do not want to leave it in the outbox, add it to the removal list
                    self.insight_articles_to_remove_from_outbox.append(article)


                    # We do want to set the related article for its match
                    for research_article in articles:
                        if research_article.doi == related_article_doi:
                            if self.logger:
                                log_info = ("Setting match on " + related_article_doi +
                                            " to " + article.doi)
                                self.admin_email_content += "\n" + log_info
                                self.logger.info(log_info)
                            research_article.set_related_insight_article(article)

                else:
                    # Set this insights related article

                    #print "No article match on " + article.doi

                    related_article_doi = article.get_article_related_insight_doi()
                    if related_article_doi:
                        related_article = self.get_related_article(related_article_doi)
                        if related_article:
                            article.set_related_insight_article(related_article)
                        else:
                            # Could not find the related article
                            if self.logger:
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
        Connect to the S3 bucket, and from the outbox folder,
        download the .xml to be processed
        """
        filenames = []

        file_extensions = []
        file_extensions.append(".xml")

        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        s3_key_names = s3lib.get_s3_key_names_from_bucket(
            bucket=bucket,
            prefix=self.outbox_folder,
            file_extensions=file_extensions)

        for name in s3_key_names:
            # Download objects from S3 and save to disk
            s3_key = bucket.get_key(name)

            filename = name.split("/")[-1]

            # Download to the activity temp directory
            dirname = self.get_tmp_dir()

            filename_plus_path = dirname + os.sep + filename

            mode = "wb"
            f = open(filename_plus_path, mode)
            s3_key.get_contents_to_file(f)
            f.close()

            filenames.append(filename_plus_path)

        return filenames

    def parse_article_xml(self, article_xml_filenames):
        """
        Given a list of article XML filenames,
        parse the files and add the article object to our article map
        """

        articles = []

        for article_xml_filename in article_xml_filenames:

            article = self.create_article()
            article.parse_article_file(article_xml_filename)
            article.pdf_cover_link = article.get_pdf_cover_page(article.doi_id, self.settings, self.logger)
            if self.logger:
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
            if self.logger:
                log_info = 'PublicationEmail email templates did not warm successfully'
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            # Stop now! Return False if we do not have the necessary files
            return False
        else:
            if self.logger:
                log_info = 'PublicationEmail email templates warmed'
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            return True

    def create_article(self, doi_id=None):
        """
        Instantiate an article object and optionally populate it with
        data for the doi_id (int) supplied
        """

        # Instantiate a new article object
        article = articlelib.article(self.settings, self.get_tmp_dir())

        if doi_id:
            # Get and parse the article XML for data
            # Convert the doi_id to 5 digit string in case it was an integer
            if type(doi_id) == int:
                doi_id = str(doi_id).zfill(5)
            article_xml_filename = article.download_article_xml_from_s3(doi_id)
            try:
                article.parse_article_file(self.get_tmp_dir() + os.sep + article_xml_filename)
            except:
                # Article XML for this DOI was not parsed so return None
                return None

        return article


    def get_related_article(self, doi):
        """
        When populating related articles, given a DOI,
        download the article XML and parse it,
        return a previously parsed article object if it exists
        """

        article = None

        for article in self.related_articles:
            if article.doi == doi:
                # Return an existing article object
                if self.logger:
                    log_info = "Hit the article cache on " + doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                return article

        # Article for this DOI does not exist, populate it
        doi_id = int(doi.split(".")[-1])
        article = self.create_article(doi_id)

        if not article:
            if self.logger:
                log_info = "Could not build the related article " + doi
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            return article

        self.related_articles.append(article)

        if self.logger:
            log_info = "Building article for " + doi
            self.admin_email_content += "\n" + log_info
            self.logger.info(log_info)

        return article

    def is_feature_article(self, article):
        if (article.is_in_display_channel("Feature article") is True or
            article.is_in_display_channel("Feature Article") is True):
            return True
        return False

    def approve_articles(self, articles):
        """
        Given a list of article objects, approve them for processing
        """

        approved_articles = []

        # Keep track of which articles to remove at the end
        remove_article_doi = []

        # Remove based on article type
        for article in articles:
            if article.article_type in self.article_types_do_not_send:
                if self.logger:
                    log_info = "Removing based on article type " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                remove_article_doi.append(article.doi)

        for article in articles:
            # Check whether the DOI was ever POA
            article.was_ever_poa = lax_provider.was_ever_poa(article.doi_id, self.settings)

            # Now can check if published
            is_published = lax_provider.published_considering_poa_status(
                article_id=article.doi_id,
                settings=self.settings,
                is_poa=article.is_poa,
                was_ever_poa=article.was_ever_poa)
            if is_published is not True:
                if self.logger:
                    log_info = "Removing because it is not published " + article.doi
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)
                remove_article_doi.append(article.doi)

        # Can remove the articles now without affecting the loops using del
        for article in articles:
            if article.doi not in remove_article_doi:
                approved_articles.append(article)

        return approved_articles


    def send_email_testrun(self, email_types, elife_id, authors, article):
        """
        For testing the workflow and the templates
        Given an article (and its elife_id), list of email types and
        list of authors, it will send lots of emails
        and also bypass the default allow_duplicates value
        Should only be run on the dev environment which should not have live email addresses on it
        """

        # Failsafe check, do not continue if we think we are not on the dev environment
        # Expecting    self.settings.bucket = 'elife-articles-dev'  look for the dev at the end
        if self.settings.bucket.split('-')[-1] != 'dev':
            return

        # Allow duplicates, will send
        self.allow_duplicates = True

        # Send an email to each author
        for author in authors:
            # Test sending each type of template
            for email_type in self.email_types:
                result = self.send_email(email_type, elife_id, author, article, authors)

            # For testing set the article as its own related article then send again

            # Look for a related article, if not found, set the article to be related to itself
            related_article_doi = article.get_article_related_insight_doi()
            if related_article_doi is None:
                related_article_doi = article.doi_url

            related_article = self.get_related_article(related_article_doi)
            article.set_related_insight_article(related_article)
            for email_type in ['author_publication_email_VOR_no_POA',
                               'author_publication_email_VOR_after_POA']:
                result = self.send_email(email_type, elife_id, author, article, authors)

    def choose_recipient_authors(self, authors, article_type, feature_article,
                                 related_insight_article):
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
            if type(self.settings.features_publication_recipient_email) == list:
                for email in self.settings.features_publication_recipient_email:
                    recipient_email_list.append(email)
            else:
                recipient_email_list.append(self.settings.features_publication_recipient_email)

            for recipient_email in recipient_email_list:
                feature_author = {}
                feature_author["first_nm"] = "Features"
                feature_author["e_mail"] = recipient_email
                # Special: convert the dict to an object for use in templates
                obj = Struct(**feature_author)
                recipient_authors.append(obj)

        if authors and len(recipient_authors) > 0:
            recipient_authors = recipient_authors + authors
        elif authors:
            recipient_authors = authors

        return recipient_authors


    def send_email(self, email_type, elife_id, author, article, authors):
        """
        Given the email type and author,
        decide whether to send the email (after checking for duplicates)
        and queue the email
        """

        if author is None:
            return False
        if not hasattr(author, 'e_mail'):
            return False
        if author.e_mail is not None and str(author.e_mail).strip() == "":
            return False
        if author.e_mail is None:
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
            log_info = ('Failed to load email headers for: doi_id: %s email_type: %s recipient_email: %s' %
                        (str(elife_id), str(email_type), str(author.e_mail)))
            self.admin_email_content += "\n" + log_info
            return False

        # Get the article published date timestamp
        pub_date_timestamp = None
        date_scheduled_timestamp = 0
        try:
            pub_date_timestamp = article.pub_date_timestamp
            date_scheduled_timestamp = pub_date_timestamp
        except:
            pass

        try:
            # Duplicate email check, can bypass with allow_duplicates = True
            if self.allow_duplicates is True:
                duplicate = False
            else:
                duplicate = self.is_duplicate_email(
                    doi_id=elife_id,
                    email_type=headers["email_type"],
                    recipient_email=author.e_mail)

            if duplicate is True:
                if self.logger:
                    log_info = ('Duplicate email: doi_id: %s email_type: %s recipient_email: %s' %
                                (str(elife_id), str(email_type), str(author.e_mail)))
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)

            # Secondly, check if article is on the do not send list
            if duplicate is False and self.allow_duplicates is not True:
                duplicate = self.is_article_do_not_send(elife_id)

                if duplicate is True:
                    if self.logger:
                        log_info = (('Article on do not send list for DOI: doi_id: %s ' +
                                    'email_type: %s recipient_email: %s') %
                                    (str(elife_id), str(email_type), str(author.e_mail)))
                        self.admin_email_content += "\n" + log_info
                        self.logger.info(log_info)

            # Now we can actually queue the email to be sent
            if duplicate is False:
                # Queue the email
                if self.logger:
                    log_info = ("Sending " + email_type + " type email" +
                                " for article " + str(elife_id) +
                                " to recipient_email " + str(author.e_mail))
                    self.admin_email_content += "\n" + log_info
                    self.logger.info(log_info)

                self.queue_author_email(
                    email_type=email_type,
                    author=author,
                    headers=headers,
                    article=article,
                    authors=authors,
                    doi_id=elife_id,
                    date_scheduled_timestamp=date_scheduled_timestamp,
                    format="html")

            return True
        except Exception:
            if self.logger:
                self.logger.exception("An error has occurred on send_email method")
                pass

    def queue_author_email(self, email_type, author, headers, article, authors, doi_id,
                           date_scheduled_timestamp, format="html"):
        """
        Format the email body and add it to the live queue
        Only call this to send actual emails!
        """
        body = self.templates.get_email_body(
            email_type=email_type,
            author=author,
            article=article,
            authors=authors,
            format=format)

        # Add the email to the email queue
        self.db.elife_add_email_to_email_queue(
            recipient_email=author.e_mail,
            sender_email=headers["sender_email"],
            email_type=headers["email_type"],
            format=headers["format"],
            subject=headers["subject"],
            body=body,
            doi_id=doi_id,
            date_scheduled_timestamp=date_scheduled_timestamp)

    def is_duplicate_email(self, doi_id, email_type, recipient_email):
        """
        Use the SimpleDB provider to count the number of emails
        in the queue for the particular combination of variables
        to determine whether we should not send an email twice
        Default: return None
          No matching emails: return False
          Is a matching email in the queue: return True
        """
        duplicate = None
        try:
            count = 0

            # Count all emails of all sent statuses
            for sent_status in True, False, None:
                result_list = self.db.elife_get_email_queue_items(
                    query_type="count",
                    doi_id=doi_id,
                    email_type=email_type,
                    recipient_email=recipient_email,
                    sent_status=sent_status
                )

                count_result = result_list[0]
                count += int(count_result["Count"])

            # Now make a decision on how many emails counted
            if count > 0:
                duplicate = True
            elif count == 0:
                duplicate = False

        except:
            # Do nothing, we will return the default
            pass

        return duplicate

    def get_to_folder_name(self):
        """
        From the date_stamp
        return the S3 folder name to save published files into
        """
        to_folder = None

        date_folder_name = self.date_stamp
        to_folder = self.published_folder + date_folder_name + "/"

        return to_folder

    def clean_outbox(self):
        """
        Clean out the S3 outbox folder
        """

        to_folder = self.get_to_folder_name()

        # Move only the published files from the S3 outbox to the published folder
        bucket_name = self.publish_bucket

        # Connect to S3 and bucket
        s3_conn = S3Connection(self.settings.aws_access_key_id, self.settings.aws_secret_access_key)
        bucket = s3_conn.lookup(bucket_name)

        # Concatenate the expected S3 outbox file names
        s3_key_names = []

        # Compile a list of the published file names
        remove_doi_list = []
        processed_file_names = []
        for article in self.articles_approved_prepared:
            if article.doi not in self.articles_do_not_remove_from_outbox:
                remove_doi_list.append(article.doi)

        for article in self.insight_articles_to_remove_from_outbox:
            remove_doi_list.append(article.doi)

        for k, v in self.xml_file_to_doi_map.items():
            if k in remove_doi_list:
                processed_file_names.append(v)

        for name in processed_file_names:
            filename = name.split(os.sep)[-1]
            s3_key_name = self.outbox_folder + filename
            s3_key_names.append(s3_key_name)

        for name in s3_key_names:
            # Download objects from S3 and save to disk

            # Do not delete the from_folder itself, if it is in the list
            if name != self.outbox_folder:
                filename = name.split("/")[-1]
                new_s3_key_name = to_folder + filename

                # First copy
                new_s3_key = None
                try:
                    new_s3_key = bucket.copy_key(new_s3_key_name, bucket_name, name)
                except:
                    pass

                # Then delete the old key if successful
                if isinstance(new_s3_key, boto.s3.key.Key):
                    old_s3_key = bucket.get_key(name)
                    old_s3_key.delete()


    def get_authors(self, doi_id=None, corresponding=None, local_document=None):
        """
        Using the EJP data provider, get the column headings
        and author data, and reassemble into a list of authors
        document is only provided when running tests, otherwise just specify the doi_id
        """
        author_list = []
        (column_headings, authors) = self.ejp.get_authors(doi_id=doi_id,
                                                          corresponding=corresponding,
                                                          local_document=local_document)

        # Authors will be none if there is not data
        if authors is None:
            if self.logger:
                log_info = "No authors found for article doi id " + str(doi_id)
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            return None

        for author in authors:
            i = 0
            temp = {}
            for value in author:
                heading = column_headings[i]
                temp[heading] = value
                i = i + 1
            # Special: convert the dict to an object for use in templates
            obj = Struct(**temp)
            author_list.append(obj)

        return author_list

    def get_editors(self, doi_id=None, local_document=None):
        """
        Using the EJP data provider, get the column headings
        and editor data, and reassemble into a list of editors
        document is only provided when running tests, otherwise just specify the doi_id
        """
        editor_list = []
        (column_headings, editors) = self.ejp.get_editors(doi_id=doi_id, local_document=local_document)

        # Editors will be none if there is not data
        if editors is None:
            if self.logger:
                log_info = "No editors found for article doi id " + str(doi_id)
                self.admin_email_content += "\n" + log_info
                self.logger.info(log_info)
            return None

        for editor in editors:
            i = 0
            temp = {}
            for value in editor:
                heading = column_headings[i]
                temp[heading] = value
                i = i + 1
            # Special: convert the dict to an object for use in templates
            obj = Struct(**temp)
            editor_list.append(obj)

        return editor_list

    def is_article_do_not_send(self, doi_id):
        """
        Check if article is on the do not send email list
        This is used to not send a publication email when an article is correct
        For articles published prior to the launch of this publication email feature
          we cannot check the log of all emails sent to check if a duplicate
          email exists already
        """

        # Convert to string for matching
        if type(doi_id) == int:
            doi_id = str(doi_id).zfill(5)

        if doi_id in blacklist.publication_email_article_do_not_send_list():
            return True
        else:
            return False


    def send_admin_email(self):
        """
        After do_activity is finished, send emails to recipients
        on the status of the activity
        """
        # Connect to DB
        db_conn = self.db.connect()

        # Note: Create a verified sender email address, only done once
        #conn.verify_email_address(self.settings.ses_sender_email)

        current_time = time.gmtime()

        body = self.get_admin_email_body(current_time)
        subject = self.get_admin_email_subject(current_time)
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = []
        # Handle multiple recipients, if specified
        if type(self.settings.ses_admin_email) == list:
            for email in self.settings.ses_admin_email:
                recipient_email_list.append(email)
        else:
            recipient_email_list.append(self.settings.ses_admin_email)

        for email in recipient_email_list:
            # Add the email to the email queue
            self.db.elife_add_email_to_email_queue(
                recipient_email=email,
                sender_email=sender_email,
                email_type="PublicationEmail",
                format="text",
                subject=subject,
                body=body)


        return True

    def get_activity_status_text(self, activity_status):
        """
        Given the activity status boolean, return a human
        readable text version
        """
        if activity_status is True:
            activity_status_text = "Success!"
        else:
            activity_status_text = "FAILED."

        return activity_status_text

    def get_admin_email_subject(self, current_time):
        """
        Assemble the email subject
        """
        date_format = '%Y-%m-%d %H:%M'
        datetime_string = time.strftime(date_format, current_time)

        activity_status_text = self.get_activity_status_text(self.activity_status)

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

        activity_status_text = self.get_activity_status_text(self.activity_status)

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



class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

