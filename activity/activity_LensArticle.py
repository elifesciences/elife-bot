import json
import os
import codecs
from provider import utils
from provider.storage_provider import storage_context
import provider.templates as templatelib
import provider.article as articlelib
from activity.objects import Activity

"""
LensArticle activity
"""


class activity_LensArticle(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_LensArticle, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "LensArticle"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Create a lens article index.html page for the particular article."
        )

        # Templates provider
        self.templates = templatelib.Templates(settings, self.get_tmp_dir())

        # article data provider
        self.article = articlelib.article(settings, self.get_tmp_dir())

        # Default templates directory
        self.from_dir = "template"

        # CDN bucket
        self.cdn_bucket = settings.publishing_buckets_prefix + settings.ppp_cdn_bucket

        self.article_xml_filename = None
        self.article_s3key = None
        self.article_html = None

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        article_id = None
        # Support for both the starter method and the PostPerfectPublication method
        if data and "article_id" in data:
            article_id = data["article_id"]

        self.article_xml_filename = self.article.download_article_xml_from_s3(
            doi_id=article_id
        )

        if not self.article_xml_filename:
            if self.logger:
                self.logger.info(
                    "LensArticle article xml file not found for %s" % str(article_id)
                )
            return True

        self.article.parse_article_file(
            self.get_tmp_dir() + os.sep + self.article_xml_filename
        )

        # Check for PoA, we will not create lens article for
        if self.article.is_poa:
            if self.logger:
                self.logger.info(
                    "LensArticle %s is PoA, not creating a lens page" % str(article_id)
                )
            return True

        self.article_s3key = self.get_article_s3key(article_id)

        filename = "index.html"

        self.article_html = self.get_article_html(
            from_dir=self.from_dir,
            article=self.article,
            cdn_bucket=self.cdn_bucket,
            article_xml_filename=self.article_xml_filename,
        )

        # Write the document to disk first
        filename_plus_path = self.write_html_file(self.article_html, filename)

        # Now, set the S3 object to the contents of the filename
        storage = storage_context(self.settings)
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.lens_bucket
            + "/"
            + self.article_s3key
        )
        metadata = {"ContentType": "text/html"}
        storage.set_resource_from_filename(s3_resource, filename_plus_path, metadata)

        if self.logger:
            self.logger.info("LensArticle created for: %s" % self.article_s3key)

        return True

    def get_article_s3key(self, article_id):
        """
        Given an eLife article DOI ID (5 digits) assemble the
        S3 key name for where to save the article index.html page
        """
        article_s3key = utils.pad_msid(article_id) + "/index.html"

        return article_s3key

    def get_article_html(self, from_dir, article, cdn_bucket, article_xml_filename):
        """
        Given the URL of the article XML file, create a lens article index.html page
        using header, footer or template, as required
        """

        if from_dir is None:
            from_dir = self.from_dir

        article_html = self.templates.get_lens_article_html(
            from_dir, article, cdn_bucket, article_xml_filename
        )

        return article_html

    def write_html_file(self, article_html, filename):
        """
        Write the HTML to the disk
        """

        filename_plus_path = self.get_tmp_dir() + os.sep + filename
        mode = "w"
        with codecs.open(filename_plus_path, mode, encoding="utf8") as open_file:
            open_file.write(article_html)

        return filename_plus_path
