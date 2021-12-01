import json
import os
import glob
import shutil
from jinja2 import Environment, FileSystemLoader


"""
Templates provider
Copies and parses templates using jinja2
"""


class Templates(object):
    def __init__(self, settings=None, tmp_dir=None):
        self.settings = settings
        self.tmp_dir = tmp_dir

        # Default tmp_dir if not specified
        self.tmp_dir_default = "templates_provider"

        # Jinja stuff
        self.jinja_env = None

        # Track whether templates are downloaded and ready for use
        self.email_templates_warmed = False
        self.lens_templates_warmed = False

    def get_tmp_dir(self):
        """
        Get the temporary file directory, but if not set
        then make the directory
        """
        if self.tmp_dir:
            return self.tmp_dir
        else:
            self.tmp_dir = self.tmp_dir_default

        return self.tmp_dir

    def copy_lens_templates(self, from_dir):
        """
        Prepare the tmp_dir jinja template directory
        to hold template files used in author publication
        and editor publication emails
        """
        template_list = ["lens_article.html"]

        template_missing = False

        for template in template_list:
            try:
                file_path = os.path.join(from_dir, template)
                shutil.copy(file_path, self.get_tmp_dir())
            except:
                template_missing = True

        if template_missing:
            self.lens_templates_warmed = False
        elif template_missing is False:
            self.lens_templates_warmed = True

    def copy_email_templates(self, from_dir):
        "copy email templates from from_dir to the tmp_dir"
        template_file_paths = []
        for file_type in ["html", "json"]:
            match_pattern = "%s/*.%s" % (from_dir, file_type)
            template_file_paths += glob.glob(match_pattern)
        for file_path in template_file_paths:
            shutil.copy(file_path, self.get_tmp_dir())
        self.email_templates_warmed = True

    def get_jinja_env(self):
        """
        Instantiate the jinja template environment
        if it does not already exist
        Use a file system loader from the tmp_dir as the root
        """

        if self.jinja_env is None:
            loader = FileSystemLoader(self.get_tmp_dir())
            self.jinja_env = Environment(loader=loader)

        return self.jinja_env

    def get_jinja_template(self, jinja_env, template_name):

        template = jinja_env.get_template(template_name)

        return template

    def get_email_body(self, email_type, author, article, authors, format="html"):
        """
        Given the email type and data objects, load the jinja environment,
        get the template, render it and return the
        email body
        """

        # Warm the template files
        if self.email_templates_warmed is not True:
            raise Exception(
                "Templates no warmed in templates provider get_email_body()"
            )

        if format == "html":
            template_name = email_type + ".html"
        elif format == "text":
            template_name = email_type + ".txt"

        # Check again, in case the template warm was not successful
        if self.email_templates_warmed is True:

            jinja_env = self.get_jinja_env()
            tmpl = self.get_jinja_template(jinja_env, template_name)
            body = tmpl.render(author=author, article=article, authors=authors)
            return body

        else:
            return None

    def get_email_headers(self, email_type, author, article, format="html"):
        """
        Given the email type and data objects, load the jinja environment,
        get the template, render it and return the
        email headers
        """

        # Warm the template files
        if self.email_templates_warmed is not True:
            raise Exception(
                "Templates no warmed in templates provider get_email_headers()"
            )

        template_name = email_type + ".json"

        # Check again, in case the template warm was not successful
        if self.email_templates_warmed is True:

            jinja_env = self.get_jinja_env()
            tmpl = self.get_jinja_template(jinja_env, template_name)
            # fix special characters in subject
            article = article_title_char_escape(article)
            headers_str = tmpl.render(author=author, article=article)
            headers = json.loads(headers_str)
            # Add the email format as specified
            headers["format"] = format
            return headers
        else:
            return None

    def get_lens_article_html(
        self, from_dir, article, cdn_bucket, article_xml_filename
    ):
        """
        Given data objects, load the jinja environment,
        get the template, render it and return the content
        """

        # Warm the template files
        if self.lens_templates_warmed is not True:
            self.copy_lens_templates(from_dir)

        # Check again, in case the template warm was not successful
        if self.lens_templates_warmed is True:

            jinja_env = self.get_jinja_env()
            tmpl = self.get_jinja_template(jinja_env, "lens_article.html")
            content = tmpl.render(
                article=article,
                cdn_bucket=cdn_bucket,
                article_xml_filename=article_xml_filename,
            )
            return content
        else:
            return None


def email_headers(
    templates_object, email_type, recipient, article, email_format="html", logger=None
):
    """Email headers for the template customised with data provided

    :param templates_object: Templates object
    :param email_type: the type of email template to render
    :param recipient: recipient of the email, a dict or object with values
    :param article: article object
    :param email_format: format of the email, html or text
    :param logger: log.logger object
    :returns: dict of email headers from the rendered template
    """
    try:
        headers = templates_object.get_email_headers(
            email_type=email_type,
            author=recipient,
            article=article,
            format=email_format,
        )
    except Exception as exception:
        log_info = (
            "Failed to load email headers for: article: %s email_type: %s recipient: %s"
            % (str(article), str(email_type), str(recipient))
        )
        if logger:
            logger.info(log_info)
            logger.exception(str(exception))
    return headers


def email_body(
    templates_object,
    email_type,
    recipient,
    article,
    authors=None,
    email_format="html",
    logger=None,
):
    """Email body for the template customised with data provided

    :param templates_object: Templates object
    :param email_type: the type of email template to render
    :param recipient: recipient of the email, a dict or object with values
    :param article: article object
    :param email_format: format of the email, html or text
    :param logger: log.logger object
    :returns: string body from the rendered template
    """
    try:
        body = templates_object.get_email_body(
            email_type=email_type,
            author=recipient,
            article=article,
            authors=authors,
            format=email_format,
        )
    except Exception as exception:
        log_info = (
            "Failed to load email body for: article: %s email_type: %s recipient: %s"
            % (str(article), str(email_type), str(recipient))
        )
        if logger:
            logger.info(log_info)
            logger.exception(str(exception))
    return body


def json_char_escape(string):
    return string.replace("\\", "\\\\").replace('"', '\\"')


def article_title_char_escape(article):
    """escape characters in article object article_title for JSON parsing"""
    if hasattr(article, "article_title"):
        article.article_title = json_char_escape(article.article_title)
    if isinstance(article, dict) and "article_title" in article:
        article["article_title"] = json_char_escape(article["article_title"])
    return article
