"functions for generating preprint XML"
import os
from elifearticle.parse import build_article_from_xml
from elifearticle.article import (
    Article,
    ArticleDate,
    Contributor,
    Event,
    License,
)
from jatsgenerator import generate
from jatsgenerator.conf import raw_config, parse_raw_config
from provider import cleaner, download_helper, utils


CONFIG_SECTION = "elife_preprint"

# path in the bucket for preprint XML
PREPRINT_AUTOMATION_XML_PATH_PATTERN = "automation/{article_id}/v{version}"

# file name of the preprint XML in the bucket
PREPRINT_AUTOMATION_XML_FILE_NAME_PATTERN = "article-source.xml"


# DOI prefix to confirm version DOI value
DOI_PREFIX = "10.7554"


class PreprintArticleException(Exception):
    pass


def jatsgenerator_config(config_section, config_file):
    "parse the config values from the jatsgenerator config"
    return parse_raw_config(raw_config(config_section, config_file))


def build_article(article_id, docmap_string, article_xml_path, version=None):
    "collect data from docmap and preprint XML to populate an Article object"
    newest_version_doi = cleaner.version_doi_from_docmap(docmap_string, article_id)

    if not newest_version_doi:
        raise PreprintArticleException(
            "Could not find a newest_version_doi for article_id %s" % article_id
        )

    if not newest_version_doi.startswith(DOI_PREFIX):
        raise PreprintArticleException(
            "newest_version_doi %s for article_id %s has an incorrect prefix"
            % (newest_version_doi, article_id)
        )

    if version:
        # build an XML file for a specific version, using docmap data for that preprint version
        version_doi = ".".join([newest_version_doi.rsplit(".", 1)[0], str(version)])
    else:
        # otherwise use the most recent version DOI
        version_doi = newest_version_doi

    # get concept DOI from the version DOI
    doi, version = utils.version_doi_parts(version_doi)

    # instantiate the Article
    article = Article(doi)
    article.article_type = "preprint"
    article.version_doi = version_doi
    article.manuscript = article_id

    # get publication history
    pub_history_data = cleaner.docmap_preprint_history_from_docmap(docmap_string)
    posted_date_string = None
    for history_event in pub_history_data:
        # only add events equal to or less than the version value
        if history_event.get("doi"):
            event_doi, event_version = history_event.get("doi").rsplit(".", 1)
            if (
                history_event.get("type") in ["preprint", "reviewed-preprint"]
                and event_doi == doi
                and int(event_version) > int(version)
            ):
                continue
        # look for the posted_date
        if (
            history_event.get("type") in ["preprint", "reviewed-preprint"]
            and history_event.get("doi") == version_doi
        ):
            posted_date_string = history_event.get("date")
        else:
            # otherwise add it as an event to the Article publication_history
            preprint_event = Event()
            preprint_event.event_type = history_event.get("type")
            preprint_event.date = cleaner.date_struct_from_string(
                history_event.get("date")
            )
            preprint_event.uri = utils.get_doi_url(history_event.get("doi"))
            article.publication_history.append(preprint_event)
    if not posted_date_string:
        # no posted date found
        raise PreprintArticleException(
            "Could not find a date in the history events for article_id %s" % article_id
        )
    # add posted_date to the Article
    posted_date_struct = cleaner.date_struct_from_string(posted_date_string)
    article.add_date(ArticleDate("posted_date", posted_date_struct))

    # volume from year of the first reviewed-preprint
    article.volume = cleaner.volume_from_docmap(docmap_string, article_id)

    # license
    for history_event in pub_history_data:
        if (
            history_event.get("type") in ["reviewed-preprint"]
            and history_event.get("doi") == version_doi
            and history_event.get("license")
        ):
            license_object = License()
            license_object.href = history_event.get("license")
            article.license = license_object

    # copy metadata from an article XML file
    preprint_article, error_count = build_article_from_xml(
        article_xml_path, detail="full"
    )
    # title
    article.title = preprint_article.title
    # abstract
    abstract = None
    if preprint_article.abstract:
        abstract = (
            preprint_article.abstract.replace("<p>", " ")
            .replace("</p>", " ")
            .lstrip()
            .rstrip()
        )
    article.abstract = abstract
    # contributors
    article.contributors = preprint_article.contributors
    # references
    article.ref_list = preprint_article.ref_list

    # sub-article data from docmap and Sciety web content
    external_data = cleaner.sub_article_data(
        docmap_string, article, version_doi, generate_dois=False
    )
    # populate sub-article contributor values
    for index, data_item in enumerate(external_data):
        # 1. assessment
        if data_item.get("article").article_type == "editor-report":
            # editor is already set from docmap data
            pass
        # 2. public reviews
        if data_item.get("article").article_type == "referee-report":
            # anonymous contributor
            anonymous_contributor = Contributor("author", None, None)
            anonymous_contributor.anonymous = True
            external_data[index]["article"].contributors = [anonymous_contributor]
        # 3. author response
        if data_item.get("article").article_type == "author-comment":
            # copy the authors of the parent article
            external_data[index]["article"].contributors = [
                author
                for author in article.contributors
                if author.contrib_type == "author"
            ]

    # add the review articles to the article
    for review_article_data in external_data:
        article.review_articles.append(review_article_data.get("article"))

    return article


def xml_filename(article_id, settings, version=None):
    "preprint XML filename from the configuration file"
    jats_config = jatsgenerator_config(
        CONFIG_SECTION, settings.jatsgenerator_config_file
    )
    filename = jats_config.get("xml_filename_pattern").format(manuscript=article_id)
    if version:
        filename = filename.replace(".xml", "-v%s.xml" % version)
    return filename


def preprint_xml(article, settings):
    "generate preprint XML string from inputs"
    add_comment = True
    jats_config = jatsgenerator_config(
        CONFIG_SECTION, settings.jatsgenerator_config_file
    )
    article_xml = generate.ArticleXML(article, jats_config, add_comment)
    xml_string = article_xml.output_xml(pretty=True, indent="")
    return xml_string


def download_original_preprint_xml(settings, to_dir, article_id, version):
    "download the preprint server version of the XML"
    # get preprint server XML from a bucket
    real_filename = PREPRINT_AUTOMATION_XML_FILE_NAME_PATTERN
    bucket_name = settings.epp_data_bucket
    bucket_folder = PREPRINT_AUTOMATION_XML_PATH_PATTERN.format(
        article_id=article_id, version=version
    )

    article_xml_path = download_helper.download_file_from_s3(
        settings,
        real_filename,
        bucket_name,
        bucket_folder,
        to_dir,
    )

    return article_xml_path


def build_preprint_article(
    settings, article_id, version, docmap_string, temp_dir, logger
):
    "download original preprint XML and with the docmap string populate an article object"

    # get preprint server XML from a bucket
    try:
        article_xml_path = download_original_preprint_xml(
            settings, temp_dir, article_id, version
        )
    except Exception as exception:
        # handle if original preprint XML could not be downloaded
        raise PreprintArticleException(
            logger.exception(
                "Exception getting preprint server XML"
                " from the bucket for article_id %s, version %s: %s"
                % (
                    article_id,
                    version,
                    str(exception),
                )
            )
        )

    try:
        article = build_article(article_id, docmap_string, article_xml_path, version)
    except PreprintArticleException as exception:
        # handle if article could not be built
        logger.exception(str(exception))
        raise

    # continue if article could be populated
    return article


def generate_preprint_xml(
    settings, article_id, version, caller_name, directories, logger
):
    "generate preprint XML and save it to disk"
    # get docmap data
    try:
        docmap_string = cleaner.get_docmap_string_with_retry(
            settings, article_id, caller_name, logger
        )
    except Exception as exception:
        logger.exception(
            (
                "%s, exception raised to get docmap_string"
                " using retries for article_id %s version %s"
            )
            % (caller_name, article_id, version)
        )
        raise PreprintArticleException(exception) from exception

    # populate the article object
    try:
        article = build_preprint_article(
            settings,
            article_id,
            version,
            docmap_string,
            directories.get("TEMP_DIR"),
            logger,
        )
    except Exception as exception:
        # handle if article could not be built
        logger.exception(
            "%s, exception raised when building the article object for article_id %s version %s"
            % (caller_name, article_id, version)
        )
        raise PreprintArticleException(exception) from exception

    # generate preprint XML from data sources
    xml_file_name = xml_filename(article_id, settings, version)
    xml_file_path = os.path.join(directories.get("INPUT_DIR"), xml_file_name)
    xml_string = preprint_xml(article, settings)
    with open(xml_file_path, "wb") as open_file:
        open_file.write(xml_string)

    return xml_file_path
