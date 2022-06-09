import os
import re
import urllib
import requests
from elifetools import parseJATS as parser
from provider import outbox_provider, s3lib
from provider.lax_provider import article_highest_version
from provider.storage_provider import storage_context
from provider.utils import msid_from_doi, get_doi_url, pad_msid

"""
Article data provider
From article XML, get some data for use in workflows and templates
"""


def create_article(settings, tmp_dir, doi_id=None):
    """
    Instantiate an article object and optionally populate it with
    data for the doi_id (int) supplied
    """

    # Instantiate a new article object
    article_object = article(settings)

    if doi_id:
        # Get and parse the article XML for data
        # Convert the doi_id to 5 digit string in case it was an integer
        doi_id = pad_msid(doi_id)
        article_xml_filename = article_object.download_article_xml_from_s3(
            tmp_dir, doi_id
        )
        try:
            article_object.parse_article_file(
                os.path.join(tmp_dir, article_xml_filename)
            )
        except:
            # Article XML for this DOI was not parsed so return None
            return None

    return article_object


class article:
    def __init__(self, settings=None):
        self.settings = settings

        # Some defaults
        self.related_insight_article = None
        self.was_ever_poa = None
        self.is_poa = None

        # Store the list of DOI id that was ever published
        self.doi_ids = None

    def parse_article_file(self, filename):
        """
        Given a filename to an article XML
        parse it
        """

        parsed = self.parse_article_xml(filename)

        return parsed

    def parse_article_xml(self, document):
        """
        Given article XML, parse
        it and return an object representation
        """

        try:
            soup = parser.parse_document(document)
            self.doi = parser.doi(soup)
            if self.doi:
                self.doi_id = pad_msid(msid_from_doi(self.doi))
                self.doi_url = get_doi_url(self.doi)
                self.lens_url = get_lens_url(self.doi)
                self.tweet_url = get_tweet_url(self.doi)

            self.pub_date = parser.pub_date(soup)
            self.pub_date_timestamp = parser.pub_date_timestamp(soup)

            self.article_title = parser.title(soup)
            self.article_type = parser.article_type(soup)

            self.authors = parser.authors(soup)
            self.authors_string = get_authors_string(self.authors)

            self.related_articles = parser.related_article(soup)

            self.is_poa = parser.is_poa(soup)

            # self.subject_area = self.parse_subject_area(soup)

            self.display_channel = parser.display_channel(soup)

            return True
        except:
            return False

    def download_article_xml_from_s3(self, to_dir, doi_id=None):
        """
        Return the article data for use in templates
        """

        xml_filename = None
        # Check for the document

        # Convert the value just in case
        doi_id = pad_msid(doi_id)

        article_id = doi_id
        # Get the highest published version from lax
        try:
            version = article_highest_version(article_id, self.settings)
            if not isinstance(version, int):
                return False
        except:
            return False

        if not version:
            return False

        # Download XML file via HTTP for now
        bucket_path = (
            self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
        )
        xml_file_url = (
            "http://s3-external-1.amazonaws.com/"
            + bucket_path
            + "/"
            + doi_id
            + "/"
            + "elife-"
            + doi_id
            + "-v"
            + str(version)
            + ".xml"
        )
        xml_filename = xml_file_url.split("/")[-1]
        response = requests.get(xml_file_url)
        if response.status_code == 200:
            filename_plus_path = to_dir + os.sep + xml_filename
            with open(filename_plus_path, "wb") as open_file:
                open_file.write(response.content)
            return xml_filename

        return False

    def set_related_insight_article(self, article_object):
        """
        If this article is type insight, then set the article
        the insight relates to here
        """
        self.related_insight_article = article_object

    def was_ever_published(self, doi, workflow):
        """
        For an article DOI and workflow name, check if it ever went through that workflow
        """

        doi_id = msid_from_doi(doi)

        if int(doi_id) in self.was_published_doi_ids(workflow):
            return True

        return False

    def was_published_doi_ids(self, workflow, force=False):
        """
        Get a list of S3 objects in the published folder,
        get a list of .xml files, and then parse out the article id
        """
        # Return from cached values if not force
        if force is False and self.doi_ids is not None:
            return self.doi_ids

        doi_ids = []

        # workflow e.g. "HEFCE"
        workflow_folder = outbox_provider.workflow_foldername(workflow)
        # published_folder e.g. "pub_router/published/""
        published_folder = outbox_provider.published_folder(workflow_folder)

        file_extensions = []
        file_extensions.append(".xml")

        bucket_name = self.settings.poa_packaging_bucket

        doi_ids = self.doi_ids_from_published_folder(
            bucket_name, published_folder, file_extensions
        )

        # Cache it
        self.doi_ids = doi_ids

        # Return it
        return doi_ids

    def doi_ids_from_published_folder(
        self,
        bucket_name,
        published_folder,
        file_extensions,
    ):
        """
        List objects in the S3 bucket published folder,
        get a list of files by file extensions, and then parse out the article id
        """
        ids = []

        storage = storage_context(self.settings)
        published_folder_resource = (
            self.settings.storage_provider
            + "://"
            + bucket_name
            + "/"
            + published_folder.rstrip("/")
        )
        s3_key_names = storage.list_resources(published_folder_resource)

        # Filter by file_extension
        if file_extensions is not None:
            s3_key_names = s3lib.filter_list_by_file_extensions(
                s3_key_names, file_extensions
            )

        # Extract just the doi_id portion
        for s3_key_name in s3_key_names:
            doi_id = get_doi_id_from_poa_s3_key_name(s3_key_name)
            if not doi_id:
                # Try again as vor name
                doi_id = get_doi_id_from_vor_s3_key_name(s3_key_name)

            if doi_id:
                ids.append(doi_id)

        # Remove duplicates and sort it
        ids = list(set(ids))
        ids.sort()

        return ids

    def get_article_related_insight_doi(self):
        """
        Given an article object, depending on the article_type,
        look in the list of related_articles for a particular related_article_type
        and return one article DOI only (if there are multiple return the first)
        """

        if self.article_type == "research-article":
            for related in self.related_articles:
                if related["related_article_type"] == "commentary":
                    return related["xlink_href"]

        elif self.article_type == "article-commentary":
            for related in self.related_articles:
                if related["related_article_type"] == "commentary-article":
                    return related["xlink_href"]

        # Default
        return None

    def is_in_display_channel(self, display_channel):
        """
        Given a display channel to match, return True or False if
        the article display_channel list includes it
        """

        if not hasattr(self, "display_channel"):
            # Display channel was never set
            return None

        return bool(display_channel in self.display_channel)


def get_tweet_url(doi):
    """
    Given a DOI, return a tweet URL
    """
    doi_url = get_doi_url(doi)
    params = {"text": doi_url + " @eLife"}
    return "http://twitter.com/intent/tweet?" + urllib.parse.urlencode(params)


def get_lens_url(doi):
    """
    Given a DOI, get the URL for the lens article
    """
    doi_id = pad_msid(msid_from_doi(doi))
    lens_url = "https://lens.elifesciences.org/" + doi_id
    return lens_url


def get_doi_id_from_s3_key_name(s3_key_name, file_name_prefix="elife"):
    """
    Extract just the integer doi_id value from the S3 key name
    of the article XML file
    E.g. when file_name_prefix is "elife_poa_e"
        published/20140508/elife_poa_e02419.xml = 2419
        published/20140508/elife_poa_e02444v2.xml = 2444
    E.g. when file_name_prefix is "elife" (for VOR article XML files)
        pubmed/published/20140508/elife02419.xml = 2419
    """

    doi_id = None
    delimiter = "/"
    try:
        # Split on delimiter
        file_name_with_extension = s3_key_name.split(delimiter)[-1]
        # Remove file extension
        file_name = file_name_with_extension.split(".")[0]
        # Remove file name prefix
        file_name_id = file_name.split(file_name_prefix)[-1]
        # Get the numeric part of the file name
        doi_id = int("".join(re.findall(r"^\d+", file_name_id)))
    except:
        doi_id = None

    return doi_id


def get_doi_id_from_poa_s3_key_name(s3_key_name):
    """
    Extract just the integer doi_id value from the S3 key name
    of the article XML file for a poa XML file
    E.g.
        published/20140508/elife_poa_e02419.xml = 2419
        published/20140508/elife_poa_e02444v2.xml = 2444
    """

    doi_id = None
    file_name_prefix = "elife_poa_e"

    doi_id = get_doi_id_from_s3_key_name(s3_key_name, file_name_prefix)

    return doi_id


def get_doi_id_from_vor_s3_key_name(s3_key_name):
    """
    Extract just the integer doi_id value from the S3 key name
    of the article XML file for a VOR XML file
    E.g.
        pub_router/published/20140508/elife02419.xml = 2419
    """

    doi_id = None
    file_name_prefix = "elife"

    doi_id = get_doi_id_from_s3_key_name(s3_key_name, file_name_prefix)

    return doi_id


def get_authors_string(authors):
    """
    Given a list of authors return a string for all the article authors
    """

    authors_string = ""
    for author in authors:
        if authors_string != "":
            authors_string += ", "
        if author.get("given-names"):
            authors_string += author["given-names"] + " "
        if author.get("surname"):
            authors_string += author["surname"]
        if author.get("collab"):
            authors_string += author["collab"]

    return authors_string
