"functions for generating preprint XML"
import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
import requests
from elifetools import xmlio
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
from provider.storage_provider import storage_context


CONFIG_SECTION = "elife_preprint"

# path in the bucket for preprint XML
PREPRINT_AUTOMATION_XML_PATH_PATTERN = "automation/{article_id}/v{version}"

# file name of the preprint XML in the bucket
PREPRINT_AUTOMATION_XML_FILE_NAME_PATTERN = "article-source.xml"


# file name for new preprint PDF file
PREPRINT_PDF_FILE_NAME_PATTERN = "elife-preprint-{article_id}-v{version}.pdf"


# file name for new preprint XML file
PREPRINT_XML_FILE_NAME_PATTERN = "elife-preprint-{article_id}-v{version}.xml"


# DOI prefix to confirm version DOI value
DOI_PREFIX = "10.7554"


REQUESTS_TIMEOUT = (10, 60)


class PreprintArticleException(Exception):
    pass


def jatsgenerator_config(config_section, config_file):
    "parse the config values from the jatsgenerator config"
    return parse_raw_config(raw_config(config_section, config_file))


def build_article(article_id, docmap_string, article_xml_path, version=None):
    "collect data from docmap and preprint XML to populate an Article object"
    newest_version_doi = cleaner.version_doi_from_docmap(
        docmap_string, article_id, published=True
    )

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
    article.volume = cleaner.volume_from_docmap(docmap_string, identifier=article_id)

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
    article.abstract = preprint_article.abstract
    # contributors
    article.contributors = preprint_article.contributors

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


def preprint_xml(article, settings, pretty=True, indent=""):
    "generate preprint XML string from inputs"
    add_comment = True
    jats_config = jatsgenerator_config(
        CONFIG_SECTION, settings.jatsgenerator_config_file
    )
    article_xml = generate.ArticleXML(article, jats_config, add_comment)
    xml_string = article_xml.output_xml(pretty=pretty, indent=indent)
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
    article_id, version, docmap_string, article_xml_path, logger
):
    "download original preprint XML and with the docmap string populate an article object"
    try:
        article = build_article(article_id, docmap_string, article_xml_path, version)
    except Exception as exception:
        # handle if article could not be built
        logger.exception(str(exception))
        raise PreprintArticleException(exception) from exception

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

    # get preprint server XML from a bucket
    try:
        article_xml_path = download_original_preprint_xml(
            settings, directories.get("TEMP_DIR"), article_id, version
        )
    except Exception as exception:
        # handle if original preprint XML could not be downloaded
        logger.exception(
            "%s, exception getting preprint server XML"
            " from the bucket for article_id %s version %s"
            % (
                caller_name,
                article_id,
                version,
            )
        )
        raise PreprintArticleException(exception) from exception

    # populate the article object
    try:
        article = build_preprint_article(
            article_id,
            version,
            docmap_string,
            article_xml_path,
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
    xml_string = preprint_xml(article, settings, pretty=False)

    # copy over ref-list XML
    try:
        xml_string = copy_ref_list_xml(article_xml_path, xml_string)
    except Exception as exception:
        # handle if article could not be built
        logger.exception(
            "%s, exception raised when copying ref-list XML for article_id %s version %s"
            % (caller_name, article_id, version)
        )
        # regenerate XML in pretty format
        xml_string = preprint_xml(article, settings, pretty=True, indent="")

    # output XML to file
    xml_file_name = xml_filename(article_id, settings, version)
    xml_file_path = os.path.join(directories.get("INPUT_DIR"), xml_file_name)
    with open(xml_file_path, "wb") as open_file:
        open_file.write(xml_string)

    return xml_file_path


def copy_ref_list_xml(article_xml_path, xml_string):
    "copy the ref-list from one XML file and add it to the XML string"
    preprint_article_xml_root = ElementTree.fromstring(xml_string)

    article_xml_ref_list_tag = None
    with open(article_xml_path, "r", encoding="utf-8") as open_file:
        article_xml_root = ElementTree.fromstring(open_file.read().replace("\n", ""))
        article_xml_ref_list_tag = article_xml_root.find(".//back/ref-list")

    if article_xml_ref_list_tag is not None:
        preprint_article_xml_back = preprint_article_xml_root.find(".//back")
        if preprint_article_xml_back is None:
            sub_article_tag_index = xmlio.get_first_element_index(
                preprint_article_xml_root, "sub-article"
            )
            if sub_article_tag_index:
                preprint_article_xml_root.insert(sub_article_tag_index, Element("back"))
                preprint_article_xml_back = preprint_article_xml_root.find(".//back")
            else:
                preprint_article_xml_back = SubElement(
                    preprint_article_xml_root, "back"
                )
        # append the article_xml_path ref-list into the back tag of the xml_string root
        preprint_article_xml_back.append(article_xml_ref_list_tag)

    return utils.element_xml_string(preprint_article_xml_root, pretty=True, indent="")


def is_article_preprint(article_object):
    "check properties of an Article for whether it is considered to be a preprint"
    if (
        hasattr(article_object, "publication_state")
        and article_object.article_type == "preprint"
    ) or (
        hasattr(article_object, "publication_state")
        and article_object.publication_state == "reviewed preprint"
    ):
        return True
    return False


def expanded_folder_bucket_resource(settings, bucket_name, expanded_folder_name):
    "path to the expanded folder in the bucket"
    bucket_folder_name = expanded_folder_name.replace(os.sep, "/")
    return settings.storage_provider + "://" + bucket_name + "/" + bucket_folder_name


def find_xml_filename_in_expanded_folder(settings, bucket_resource):
    "find the preprint XML file name in the bucket expanded folder"
    storage = storage_context(settings)
    s3_key_names = storage.list_resources(bucket_resource)
    # for now the only XML file is the one to download
    for s3_key_name in s3_key_names:
        if s3_key_name.endswith(".xml"):
            return s3_key_name.split("/")[-1]
    return None


def download_from_expanded_folder(
    settings, directories, bucket_filename, bucket_resource, caller_name, logger
):
    "download the object from the bucket expanded folder"
    storage = storage_context(settings)
    file_path = os.path.join(directories.get("INPUT_DIR"), bucket_filename)
    with open(file_path, "wb") as open_file:
        storage_resource_origin = bucket_resource + "/" + bucket_filename
        logger.info(
            "%s, downloading %s to %s"
            % (caller_name, storage_resource_origin, file_path)
        )
        storage.get_resource_to_file(storage_resource_origin, open_file)
    return file_path


def get_preprint_pdf_url(endpoint_url, caller_name, user_agent=None):
    "from the API endpoint, get the preprint PDF URL if it exists"
    pdf_url = None

    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}

    response = requests.get(endpoint_url, timeout=REQUESTS_TIMEOUT, headers=headers)
    if response.status_code == 200:
        data = response.json()
        pdf_url = data.get("pdf")
    elif response.status_code != 404:
        raise RuntimeError(
            "%s, got a %s status code for %s"
            % (caller_name, response.status_code, endpoint_url)
        )
    return pdf_url


def generate_new_pdf_href(article_id, version, content_subfolder):
    "generate a new name for a preprint PDF"
    new_pdf_file_name = PREPRINT_PDF_FILE_NAME_PATTERN.format(
        article_id=utils.pad_msid(article_id), version=version
    )
    new_pdf_href = "/".join(
        [part for part in [content_subfolder, new_pdf_file_name] if part]
    )
    return new_pdf_href


def clear_pdf_self_uri(xml_root):
    "remove self-uri tag if its content-type is pdf"
    article_meta_tag = xml_root.find(".//front/article-meta")
    for self_uri_tag in article_meta_tag.findall('self-uri[@content-type="pdf"]'):
        article_meta_tag.remove(self_uri_tag)


def set_pdf_self_uri_tag(xml_root, pdf_file_name, identifier):
    "modify self-uri XML tag"
    # remove old self-uri tags
    clear_pdf_self_uri(xml_root)

    # determine where to insert self-uri tag
    insert_index = 0
    article_meta_tag = xml_root.find(".//front/article-meta")
    for index, tag in enumerate(article_meta_tag.findall("*")):
        if tag.tag in ["permissions"]:
            insert_index = index + 1
            break

    # add pdf self-uri tag
    self_uri_tag = Element("self-uri")
    self_uri_tag.set("content-type", "pdf")
    self_uri_tag.set("{http://www.w3.org/1999/xlink}href", pdf_file_name)
    self_uri_tag.tail = "\n"
    article_meta_tag.insert(insert_index, self_uri_tag)


def set_pdf_self_uri(xml_file_path, pdf_file_name, identifier):
    "set or add a self-uri tag to article XML for an article PDF file"
    # Register namespaces
    xmlio.register_xmlns()

    # get the XML doctype
    xml_root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file_path,
        return_doctype_dict=True,
        return_processing_instructions=True,
    )

    set_pdf_self_uri_tag(xml_root, pdf_file_name, identifier)

    # write the XML root to disk
    cleaner.write_xml_file(
        xml_root, xml_file_path, identifier, doctype_dict, processing_instructions
    )
