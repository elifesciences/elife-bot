"functions for generating preprint XML"
from elifearticle.parse import build_article_from_xml
from elifearticle.article import Article, ArticleDate, Contributor, Event, License
from jatsgenerator import generate
from jatsgenerator.conf import raw_config, parse_raw_config
from provider import cleaner, utils


CONFIG_SECTION = "elife_preprint"

# path in the bucket to find preprint XML
PREPRINT_XML_PATH_PATTERN = "data/{article_id}/v{version}"

# file name of the preprint XML in the bucket
PREPRINT_XML_FILE_NAME_PATTERN = "{article_id}-v{version}.xml"

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
        return None

    if not newest_version_doi.startswith(DOI_PREFIX):
        raise PreprintArticleException(
            "newest_version_doi %s for article_id %s has an incorrect prefix"
            % (newest_version_doi, article_id)
        )
        return None

    if version:
        # build an XML file for a specific version, using docmap data for that preprint version
        version_doi = ".".join([newest_version_doi.rsplit(".", 1)[0], str(version)])
    else:
        # otherwise use the most recent version DOI
        version_doi = newest_version_doi

    # get concept DOI from the version DOI
    doi, version = version_doi.rsplit(".", 1)

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
    preprint_article, error_count = build_article_from_xml(article_xml_path)
    # title
    article.title = preprint_article.title
    # abstract
    article.abstract = preprint_article.abstract
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
