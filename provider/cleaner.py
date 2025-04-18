from datetime import datetime
import os
import json
import logging
import re
import time
from urllib.parse import urlparse
from xml.etree import ElementTree
from xml.etree.ElementTree import SubElement
import requests
from docmaptools import parse as docmap_parse
from elifearticle import parse as elifearticle_parse
from elifearticle.utils import license_data_by_url
from elifecleaner import (
    LOGGER,
    assessment_terms,
    block,
    configure_logging,
    equation,
    fig,
    parse,
    prc,
    pub_history,
    sub_article,
    table,
    transform,
    video,
    video_xml,
    zip_lib,
)
from elifetools import xmlio
from jatsgenerator import build
from provider import utils
from provider.storage_provider import storage_context
from provider.article_processing import file_extension

REPAIR_XML = True

LOG_FILENAME = "elifecleaner.log"
LOG_FORMAT_STRING = (
    "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
)

REQUESTS_TIMEOUT = (10, 60)


def article_id_from_zip_file(zip_file):
    "try to get an article id numeric string from a zip file name"
    id_match_pattern = re.compile(r".*\-(\d+).*\.zip$")
    matches = id_match_pattern.match(zip_file)
    if matches:
        return matches.group(1)
    return zip_file


def log_to_file(filename=None, level=logging.INFO, format_string=None):
    "configure logging to file"
    if not filename:
        filename = LOG_FILENAME
    return configure_logging(filename, level, format_string)


def configure_activity_log_handlers(log_file_path):
    "for a workflow activity configure where to log messages"
    cleaner_log_handers = []
    # log to a common log file
    cleaner_log_handers.append(log_to_file(format_string=LOG_FORMAT_STRING))

    cleaner_log_handers.append(
        log_to_file(
            log_file_path,
            format_string=LOG_FORMAT_STRING,
        )
    )
    return cleaner_log_handers


def log_remove_handler(handler):
    LOGGER.removeHandler(handler)


def unzip_zip(zip_file, tmp_dir):
    return zip_lib.unzip_zip(zip_file, tmp_dir)


def article_xml_asset(asset_file_name_map):
    return parse.article_xml_asset(asset_file_name_map)


def parse_article_xml(xml_file_path):
    # set the REPAIR_XML value
    parse.REPAIR_XML = REPAIR_XML
    # parse the XML file
    return parse.parse_article_xml(xml_file_path)


def file_list(xml_file_path):
    "get a list of files and their details from the XML"
    root = parse_article_xml(xml_file_path)
    return parse.file_list(root)


def code_file_list(xml_file_path):
    "get a list of code from the XML"
    root = parse_article_xml(xml_file_path)
    return transform.code_file_list(root)


def video_file_list(xml_file_path):
    "get a list of video files from the XML"
    files = file_list(xml_file_path)
    return video.video_file_list(files)


def cover_art_file_list(xml_file_path):
    "get a list of cover_art from the XML"
    root = parse_article_xml(xml_file_path)
    return transform.cover_art_file_list(root)


def transform_cover_art_files(
    xml_file_path, asset_file_name_map, file_transformations, identifier
):
    "rename cover art files"
    return transform.transform_cover_art_files(
        xml_file_path, asset_file_name_map, file_transformations, identifier
    )


def cover_art_file_transformations(
    cover_art_files, asset_file_name_map, article_id, identifier
):
    return transform.cover_art_file_transformations(
        cover_art_files, asset_file_name_map, article_id, identifier
    )


def glencoe_xml(xml_file_path, video_data, pretty=True, indent=""):
    return video_xml.glencoe_xml(xml_file_path, video_data, pretty, indent)


def files_by_extension(files, extension="pdf"):
    return [
        file_detail
        for file_detail in files
        if parse.file_extension(file_detail.get("upload_file_nm")) == extension
    ]


def check_files(files, asset_file_name_map, identifier):
    return parse.check_files(files, asset_file_name_map, identifier)


def transform_ejp_zip(zip_file, tmp_dir, output_dir):
    return transform.transform_ejp_zip(zip_file, tmp_dir, output_dir)


def transform_ejp_files(asset_file_name_map, output_dir, identifier):
    return transform.transform_ejp_files(asset_file_name_map, output_dir, identifier)


def is_prc(xml_file_path, zip_file_name):
    "is this a PRC article"
    # first can check the zip file name
    if "-RP" in zip_file_name:
        return True
    # next, check the XML for the status
    root = parse_article_xml(xml_file_path)
    return prc.is_xml_prc(root)


def transform_prc(xml_file_path, identifier):
    "transform PRC article XML"
    # next, check the XML for the status
    root = parse_article_xml(xml_file_path)
    prc.transform_journal_id_tags(root, identifier)
    prc.transform_journal_title_tag(root, identifier)
    prc.transform_publisher_name_tag(root, identifier)
    prc.add_prc_custom_meta_tags(root, identifier)
    write_xml_file(root, xml_file_path, identifier)


def rezip(asset_file_name_map, output_dir, zip_file_name):
    return transform.rezip(asset_file_name_map, output_dir, zip_file_name)


def video_data_from_files(files, article_id):
    return video.video_data_from_files(files, article_id)


def preprint_url(xml_file_path):
    "get the URL of the preprint from an XML file"
    root = parse_article_xml(xml_file_path)
    return parse.preprint_url(root)


def is_p_inline_graphic(tag, sub_article_id, p_tag_index, identifier):
    "see if a p tag contains only an inline-graphic tag"
    return block.is_p_inline_graphic(tag, sub_article_id, p_tag_index, identifier)


def inline_graphic_tags(xml_file_path):
    "get the inline-graphic tags from an XML file"
    root = parse_article_xml(xml_file_path)
    tags = []
    # find tags in the XML
    for inline_graphic_tag in root.findall(".//inline-graphic"):
        tags.append(inline_graphic_tag)
    return tags


def table_wrap_graphic_tags(xml_file_path):
    "find graphic tags which are inside table-wrap tags"
    root = parse_article_xml(xml_file_path)
    tags = []
    for graphic_tag in root.findall(".//table-wrap/graphic"):
        tags.append(graphic_tag)
    return tags


def tag_xlink_href(tag):
    "return a the xlink:href attribute"
    return tag.get("{http://www.w3.org/1999/xlink}href", None)


def tag_xlink_hrefs(tags):
    "return a list of xlink:href tag attributes"
    return [tag_xlink_href(tag) for tag in tags if tag_xlink_href(tag)]


def change_inline_graphic_xlink_hrefs(xml_file_path, href_to_file_name_map, identifier):
    "replace xlink:href values of inline-graphic tags with new values"
    # parse XML file
    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file_path, return_doctype_dict=True, return_processing_instructions=True
    )
    for href, new_file_name in href_to_file_name_map.items():
        for inline_graphic_tag in root.findall(
            ".//inline-graphic[@{http://www.w3.org/1999/xlink}href='%s']" % href
        ):
            if tag_xlink_href(inline_graphic_tag) == href:
                inline_graphic_tag.set(
                    "{http://www.w3.org/1999/xlink}href", new_file_name
                )
    # write XML file to disk
    encoding = "UTF-8"
    write_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        encoding=encoding,
        processing_instructions=processing_instructions,
    )


def external_hrefs(href_list):
    "return a list of xlink:href tag attributes which point to an external source"
    return [
        href
        for href in href_list
        if href and (href.startswith("https://") or href.startswith("http://"))
    ]


IMAGE_HOSTNAME_LIST = ["i.imgur.com"]


def filter_hrefs_by_hostname(href_list):
    "return href values with allowed domain names"
    return [
        href
        for href in href_list
        if href
        and urlparse(href).hostname
        and urlparse(href).hostname in IMAGE_HOSTNAME_LIST
    ]


IMAGE_FILE_EXTENSION_LIST = ["gif", "jpg", "png"]


def filter_hrefs_by_file_extension(href_list):
    "return href values with allowed file extension"
    return [
        href
        for href in href_list
        if href
        and file_extension(href)
        and file_extension(href).lower() in IMAGE_FILE_EXTENSION_LIST
    ]


def approved_inline_graphic_hrefs(href_list):
    "return a list of inline-graphic href values to download"
    # filter by hostname and file extension
    return filter_hrefs_by_file_extension(
        filter_hrefs_by_hostname(external_hrefs(href_list))
    )


def inline_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-graphic tag xlink:href values"
    return fig.inline_graphic_hrefs(sub_article_root, identifier)


def graphic_hrefs(sub_article_root, identifier):
    "return a list of graphic tag xlink:href values"
    return fig.graphic_hrefs(sub_article_root, identifier)


def table_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-formula inline-graphic tag xlink:href values"
    return table.table_graphic_hrefs(sub_article_root, identifier)


def formula_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-formula inline-graphic tag xlink:href values"
    return equation.formula_graphic_hrefs(sub_article_root, identifier)


def inline_formula_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-formula inline-graphic tag xlink:href values"
    return equation.inline_formula_graphic_hrefs(sub_article_root, identifier)


def transform_fig(sub_article_root, identifier):
    "transform inline-graphic tags into fig tags"
    return fig.transform_fig(sub_article_root, identifier)


def transform_table(sub_article_root, identifier):
    "transform inline-graphic tags into table-wrap tags"
    return table.transform_table(sub_article_root, identifier)


def table_inline_graphic_hrefs(sub_article_root, identifier):
    "return a list of inline-graphic tag xlink:href values"
    return table.table_inline_graphic_hrefs(sub_article_root, identifier)


def transform_equations(sub_article_root, identifier):
    "transform inline-graphic tags into disp-formula tags"
    return equation.transform_equations(sub_article_root, identifier)


def equation_inline_graphic_hrefs(sub_article_root, identifier):
    "get inline-graphic xlink:href values to be disp-formula"
    return equation.equation_inline_graphic_hrefs(sub_article_root, identifier)


def inline_equation_inline_graphic_hrefs(sub_article_root, identifier):
    "get inline-graphic xlink:href values to be inline-formula"
    return equation.inline_equation_inline_graphic_hrefs(sub_article_root, identifier)


def transform_inline_equations(sub_article_root, identifier):
    "transform inline-graphic tags into inline-formula tags"
    return equation.transform_inline_equations(sub_article_root, identifier)


def tsv_to_list(tsv_string):
    "parse TSV string into lists of rows"
    return table.tsv_to_list(tsv_string)


def list_to_table_xml(table_rows):
    "create a table Element tag from the table rows"
    return table.list_to_table_xml(table_rows)


def remove_tag_attributes(tag):
    "remove attributes from the tag"
    fig.remove_tag_attributes(tag)


def add_file_tag(parent, file_details):
    "add file tag to the parent tag"
    file_tag = SubElement(parent, "file")
    if file_details.get("file_type"):
        file_tag.set("file-type", file_details.get("file_type"))
    if file_details.get("upload_file_nm"):
        upload_file_nm_tag = SubElement(file_tag, "upload_file_nm")
        upload_file_nm_tag.text = file_details.get("upload_file_nm")


def add_file_tags(root, file_detail_list):
    "add file tags to the XML root"
    # find the files tag
    parent = root.find(".//article-meta/files")
    # if files tag not found, add it
    if not parent:
        article_meta_tag = root.find(".//article-meta")
        if article_meta_tag is not None:
            parent = SubElement(article_meta_tag, "files")
    for file_details in file_detail_list:
        add_file_tag(parent, file_details)


def add_file_tags_to_xml(xml_file_path, file_detail_list, identifier):
    "add file tags to the XML file"
    # parse XML file
    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file_path, return_doctype_dict=True, return_processing_instructions=True
    )
    add_file_tags(root, file_detail_list)
    # write XML file to disk
    encoding = "UTF-8"
    write_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        encoding=encoding,
        processing_instructions=processing_instructions,
    )


def populate_item_tag(parent, file_details):
    "add attributes to an item tag with file_details"
    if file_details.get("id"):
        parent.set("id", file_details.get("id"))
    if file_details.get("file_type"):
        parent.set("type", file_details.get("file_type"))
    if file_details.get("title"):
        title_tag = SubElement(parent, "title")
        title_tag.text = file_details.get("title")
    if file_details.get("href"):
        instance_tag = SubElement(parent, "instance")
        populate_instance_tag(instance_tag, file_details)


def populate_instance_tag(parent, file_details):
    "add attributes to an item instance tag"
    parent.set("href", file_details.get("href"))
    parent.set(
        "media-type", utils.content_type_from_file_name(file_details.get("href"))
    )


def add_item_tag(parent, file_details):
    "add item tag to the parent tag"
    item_tag = SubElement(parent, "item")
    populate_item_tag(item_tag, file_details)


def add_item_tags(root, file_detail_list):
    "add item tags to MECA XML root"
    # if files tag not found, add it
    for file_details in file_detail_list:
        add_item_tag(root, file_details)


def parse_manifest(xml_file_path):
    "parse MECA manifest XML"
    ElementTree.register_namespace("", "http://manuscriptexchange.org")
    return xmlio.parse(
        xml_file_path, return_doctype_dict=True, return_processing_instructions=True
    )


def write_manifest_xml_file(
    root,
    xml_asset_path,
    identifier,
    doctype_dict=None,
    processing_instructions=None,
):
    "write manifest.xml file"
    encoding = "UTF-8"
    standalone = "no"
    write_xml_file(
        root,
        xml_asset_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )
    # support for standalone
    with open(xml_asset_path, "rb") as open_file:
        xml_content = open_file.read()
    if encoding and standalone:
        xml_content = xml_content.replace(
            b'<?xml version="1.0" ?>',
            b'<?xml version="1.0" encoding="%s" standalone="%s"?>'
            % (bytes(encoding, encoding="utf-8"), bytes(standalone, encoding="utf-8")),
        )
    with open(xml_asset_path, "wb") as open_file:
        open_file.write(xml_content)


def add_item_tags_to_manifest_xml(xml_file_path, file_detail_list, identifier):
    "add items tags to MECA XML file"
    # parse XML file
    root, doctype_dict, processing_instructions = parse_manifest(xml_file_path)
    add_item_tags(root, file_detail_list)
    # write XML file to disk
    write_manifest_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )


def pretty_manifest_xml(xml_file_path, identifier):
    "add items tags to MECA XML file"
    # parse XML file
    root, doctype_dict, processing_instructions = parse_manifest(xml_file_path)
    # make pretty
    namespace = "{http://manuscriptexchange.org}"
    sub_article.tag_new_line_wrap(root)
    for item_tag in root.findall(".//%sitem" % namespace):
        sub_article.tag_new_line_wrap(item_tag)
        for tag_name in ["title"]:
            for tag in item_tag.findall(".//%s%s" % (namespace, tag_name)):
                sub_article.tag_new_line_wrap(tag)
        # wrap tail only for the following tags
        for tag_name in ["instance"]:
            for tag in item_tag.findall(".//%s%s" % (namespace, tag_name)):
                sub_article.tag_new_line_wrap_tail(tag)
    # write XML file to disk
    write_manifest_xml_file(
        root,
        xml_file_path,
        identifier,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )
    # make pretty the XML declaration
    with open(xml_file_path, "r", encoding="utf-8") as open_file:
        xml_string = open_file.read()
    xml_string = re.sub(r"\<\?xml (.*?)\?\>", r"<?xml \1?>\n", xml_string)
    xml_string = re.sub(r"\<\!DOCTYPE (.*?)\>", r"<!DOCTYPE \1>\n", xml_string)
    with open(xml_file_path, "w", encoding="utf-8") as open_file:
        open_file.write(xml_string)


def docmap_url(settings, article_id):
    "URL of the preprint docmap endpoint"
    docmap_url_pattern = getattr(settings, "docmap_url_pattern", None)
    return (
        docmap_url_pattern.format(article_id=article_id) if docmap_url_pattern else None
    )


def sub_article_data(docmap_string, article=None, version_doi=None, generate_dois=True):
    # add sub-article data from the docmap and get requests to the article object
    return sub_article.sub_article_data(
        docmap_string, article, version_doi, generate_dois
    )


def add_sub_article_xml(
    docmap_string, article_xml, terms_yaml=None, version_doi=None, generate_dois=True
):
    if terms_yaml:
        # set the path to the YAML file containing assessment terms data
        assessment_terms.ASSESSMENT_TERMS_YAML = terms_yaml
    return sub_article.add_sub_article_xml(
        docmap_string, article_xml, version_doi=version_doi, generate_dois=generate_dois
    )


def pretty_sub_article_xml(root):
    return sub_article.pretty_sub_article_xml(root)


def clean_inline_graphic_tags(root):
    "remove ext-link tags if they wrap an inline-graphic tag"
    for parent_tag in root.findall(".//ext-link/inline-graphic/../.."):
        # method is to move the child tags and text up a level, then ext-link tag can be removed
        index_delta = 0
        for index, tag in enumerate(parent_tag.findall("*")):
            if tag.tag == "ext-link":
                # move the child tags to the same place as the ext-link tag
                child_tag = None
                for child_tag in tag.findall("*"):
                    parent_tag.insert(index + index_delta, child_tag)
                    # because removing a tag alters the tag index, keep track of the index changes
                    index_delta += 1
                # add the tail if present
                if child_tag is not None and tag.tail:
                    child_tag.tail = tag.tail
                # finish up by removing the ext-link tag
                parent_tag.remove(tag)


def get_docmap(url, user_agent=None):
    "GET request for the docmap json"
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    response = requests.get(url, timeout=REQUESTS_TIMEOUT, headers=headers)
    LOGGER.info("Request to docmaps API: GET %s", url)
    LOGGER.info(
        "Response from docmaps API: %s\n%s", response.status_code, response.content
    )
    status_code = response.status_code
    if status_code not in [200]:
        raise Exception(
            "Error looking up docmap URL "
            + url
            + " in digest API: %s\n%s" % (status_code, response.content)
        )

    if status_code == 200:
        return response.content
    return None


def get_docmap_by_account_id(url, account_id, user_agent=None):
    "GET request for the docmap json and return the eLife docmap if a list is returned"
    content = get_docmap(url, user_agent=user_agent)
    if content:
        LOGGER.info("Parsing docmap content as JSON for URL %s", url)
        content_json = json.loads(content)
        if not isinstance(content_json, list):
            LOGGER.info("Only one document returned for URL %s", url)
            return content
        for list_item in content_json:
            LOGGER.info(
                "Multiple docmaps returned for URL %s, filtering by account_id %s",
                url,
                account_id,
            )
            sciety_id = list_item.get("publisher", {}).get("account", {}).get("id")
            if sciety_id and sciety_id == account_id:
                LOGGER.info(
                    "Found docmap for account_id %s from URL %s", account_id, url
                )
                return json.dumps(list_item)


def get_docmap_string(settings, article_id, identifier, caller_name, logger):
    "get a docmap string for the article from endpoint"
    # generate docmap URL
    docmap_endpoint_url = docmap_url(settings, article_id)
    logger.info("%s, docmap_endpoint_url: %s" % (caller_name, docmap_endpoint_url))
    # get docmap json
    logger.info(
        "%s, getting docmap_string for identifier: %s" % (caller_name, identifier)
    )
    return get_docmap_by_account_id(
        docmap_endpoint_url,
        settings.docmap_account_id,
        user_agent=getattr(settings, "user_agent", None),
    )


# time in seconds to sleep when a docmap string request is not successful
DOCMAP_SLEEP_SECONDS = 5
# number of times to sleep after a docmap string request is not successful
DOCMAP_RETRY = 24


def get_docmap_string_with_retry(settings, article_id, caller_name, logger):
    "get a docmap string from the endpoint and retry until reaching failure"

    tries = 0
    while tries < DOCMAP_RETRY:
        logger.info(
            "%s, try number %s to get docmap_string for article_id %s"
            % (caller_name, tries, article_id)
        )
        try:
            # get docmap as a string
            docmap_string = get_docmap_string(
                settings, article_id, article_id, caller_name, logger
            )
            break
        except Exception as exception:
            # handle if a docmap string could not be found
            logger.exception(exception)
            # sleep a short time
            time.sleep(DOCMAP_SLEEP_SECONDS)
        finally:
            tries += 1

    if tries >= DOCMAP_RETRY:
        log_message = (
            "%s, exceeded %s retries to get docmap_string for article_id %s"
            % (caller_name, DOCMAP_RETRY, article_id)
        )
        logger.info(log_message)
        raise RuntimeError(log_message)
    return docmap_string


def review_date_from_docmap(docmap_string, identifier=None):
    return prc.review_date_from_docmap(docmap_string, identifier=identifier)


def published_date_from_history(history_data, doi):
    "get published date of version version related to doi from history data"
    published_date = None
    for data in history_data:
        if (
            data.get("doi")
            and data.get("doi").startswith(doi)
            and data.get("published")
        ):
            published_date = date_struct_from_string(data.get("published"))
            break
    return published_date


def date_struct_from_string(date_string):
    return prc.date_struct_from_string(date_string)


def add_history_date(root, date_type, date_struct, identifier):
    return prc.add_history_date(root, date_type, date_struct, identifier)


def docmap_preprint(docmap_string):
    d_json = docmap_parse.docmap_json(docmap_string)
    return docmap_parse.docmap_preprint(d_json)


def docmap_preprint_history_from_docmap(docmap_string):
    d_json = docmap_parse.docmap_json(docmap_string)
    return docmap_parse.docmap_preprint_history(d_json)


def prune_history_data(history_data, doi, version):
    return pub_history.prune_history_data(history_data, doi, version)


def add_pub_history(root, history_data, docmap_string=None, identifier=None):
    return pub_history.add_pub_history(
        root, history_data, docmap_string=docmap_string, identifier=identifier
    )


def add_pub_history_meca(root, history_data, docmap_string=None, identifier=None):
    return pub_history.add_pub_history_meca(
        root, history_data, docmap_string=docmap_string, identifier=identifier
    )


def volume_from_docmap(docmap_string, version_doi=None, identifier=None):
    return prc.volume_from_docmap(
        docmap_string, version_doi=version_doi, identifier=identifier
    )


def article_id_from_docmap(docmap_string, version_doi=None, identifier=None):
    return prc.article_id_from_docmap(
        docmap_string, version_doi=version_doi, identifier=identifier
    )


def license_from_docmap(docmap_string, version_doi=None, identifier=None):
    return prc.license_from_docmap(
        docmap_string, version_doi=version_doi, identifier=identifier
    )


def elocation_id_from_docmap(docmap_string, version_doi=None, identifier=None):
    return prc.elocation_id_from_docmap(
        docmap_string, version_doi=version_doi, identifier=identifier
    )


def article_categories_from_docmap(docmap_string, version_doi=None, identifier=None):
    return prc.article_categories_from_docmap(
        docmap_string, version_doi=version_doi, identifier=identifier
    )


def version_doi_from_docmap(docmap_string, input_filename, published=True):
    return prc.version_doi_from_docmap(
        docmap_string, input_filename, published=published
    )


def next_version_doi(version_doi, input_filename):
    return prc.next_version_doi(version_doi, input_filename)


def add_doi(xml_root, doi, specific_use=None, identifier=None):
    return prc.add_doi(xml_root, doi, specific_use=specific_use, identifier=identifier)


def add_version_doi(xml_root, version_doi, input_filename):
    return prc.add_version_doi(xml_root, version_doi, input_filename)


def xml_rewrite_file_tags(xml_file_path, file_transformations, identifier):
    transform.xml_rewrite_file_tags(xml_file_path, file_transformations, identifier)


def write_xml_file(
    root,
    xml_asset_path,
    identifier,
    doctype_dict=None,
    encoding=None,
    processing_instructions=None,
):
    transform.write_xml_file(
        root,
        xml_asset_path,
        identifier,
        doctype_dict=doctype_dict,
        encoding=encoding,
        processing_instructions=processing_instructions,
    )
    # support for encoding
    with open(xml_asset_path, "rb") as open_file:
        xml_content = open_file.read()
    if encoding:
        # find xml attributes
        attribute_group = re.match(rb"\<\?xml (.*?)\?\>", xml_content)
        if attribute_group:
            # concatenate attributes including encoding
            new_attributes = b'%s encoding="%s" ' % (
                attribute_group[1].rstrip(),
                bytes(encoding, encoding="utf-8"),
            )
            # replace the xml attributes
            xml_content = re.sub(
                rb"\<\?xml .*?\?\>",
                rb"<?xml %b?>" % new_attributes,
                xml_content,
            )
    with open(xml_asset_path, "wb") as open_file:
        open_file.write(xml_content)


def bucket_asset_file_name_map(settings, bucket_name, expanded_folder):
    "list of bucket objects in the expanded_folder and return a map of object to its S3 path"
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/" + expanded_folder
    s3_key_names = storage.list_resources(orig_resource)
    # remove the expanded_folder from the s3_key_names
    short_s3_key_names = [
        key_name.replace(expanded_folder, "").lstrip("/") for key_name in s3_key_names
    ]
    return {key_name: orig_resource + "/" + key_name for key_name in short_s3_key_names}


def download_xml_file_from_bucket(settings, asset_file_name_map, to_dir, logger):
    "download article XML file from the S3 bucket expanded folder to the local disk"
    storage = storage_context(settings)
    xml_file_asset = article_xml_asset(asset_file_name_map)
    asset_key, asset_resource = xml_file_asset
    xml_file_list = [{"upload_file_nm": asset_key.rsplit("/", 1)[-1]}]
    download_asset_files_from_bucket(
        storage, xml_file_list, asset_file_name_map, to_dir, logger
    )
    return asset_file_name_map.get(asset_key)


def download_asset_files_from_bucket(
    storage, asset_file_list, asset_file_name_map, to_dir, logger
):
    "download files from the S3 bucket expanded folder to the local disk"
    # map values without folder names in order to later match XML files names to zip file path
    asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}

    for s3_file in asset_file_list:
        file_name = s3_file.get("upload_file_nm")
        asset_key = asset_key_map[file_name]
        asset_resource = asset_file_name_map.get(asset_key)
        file_path = os.path.join(to_dir, asset_key)
        logger.info("Downloading file from %s to %s" % (asset_resource, file_path))
        # create folders if they do not exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as open_file:
            storage.get_resource_to_file(asset_resource, open_file)
        # rewrite asset_file_name_map to the local value
        asset_file_name_map[asset_key] = file_path


class SettingsException(RuntimeError):
    "exception to raise if settings are missing or blank"


def verify_settings(settings, settings_required, activity_name, identifier):
    "check for missing or blank settings values"
    for settings_name in settings_required:
        if not hasattr(settings, settings_name):
            message = "%s, %s settings credential %s is missing" % (
                activity_name,
                identifier,
                settings_name,
            )
            raise SettingsException(message)
        if not getattr(settings, settings_name):
            message = "%s, %s settings credential %s is blank" % (
                activity_name,
                identifier,
                settings_name,
            )
            raise SettingsException(message)


MULTI_PAGE_FIGURE_PDF_COMMENTS = (
    'Exeter: "%s" is a PDF file made up of more than one page. '
    "Please check if there are images on numerous pages. "
    "If that's the case, please add the following author query: "
    '"Please provide this figure in a single-page format. '
    "If this would render the figure unreadable, "
    'please provide this as separate figures or figure supplements."'
)

WELLCOME_FUNDING_COMMENTS = (
    "Exeter: funding message text updated. "
    "Please add the following author query under the funding statement: "
    "We have updated the funding statement based on your Wellcome funding "
    "to include Wellcome's open access policy statement. "
    "Please confirm whether the revised wording is acceptable."
)


def production_comments(log_content):
    "format log messages into production comment messages"
    comments = []
    log_messages = utils.unicode_encode(log_content).split("\n") if log_content else []
    warning_match_pattern = re.compile(r"WARNING elifecleaner:parse:(.*?): (.*)")
    for message in log_messages:
        message_parts = warning_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if message_type == "check_multi_page_figure_pdf":
            pdf_file_name = message_content.rsplit("/", 1)[-1]
            comments.append(MULTI_PAGE_FIGURE_PDF_COMMENTS % pdf_file_name)
        else:
            # by default add the message as written
            comments.append(message_content)
    # add messages related to transform INFO log content
    transform_info_match_pattern = re.compile(
        r"INFO elifecleaner:transform:(.*?): (.*)"
    )
    for message in log_messages:
        message_parts = transform_info_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if (
            message_type == "transform_xml_funding"
            and "adding the WELLCOME_FUNDING_STATEMENT to the funding-statement"
            in message_content
        ):
            comments.append(WELLCOME_FUNDING_COMMENTS)
    # add messages related to parse INFO log content
    parse_info_match_pattern = re.compile(r"INFO elifecleaner:parse:(.*?): (.*)")
    for message in log_messages:
        message_parts = parse_info_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if message_type == "parse_article_xml":
            comments.append(message_content)
    # add messages related to video duplicate detection and renaming
    video_info_match_pattern = re.compile(r"INFO elifecleaner:video:(.*?): (.*)")
    for message in log_messages:
        message_parts = video_info_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if message_type in ["all_terms_map", "renumber", "renumber_term_map"]:
            comments.append(message_content)
    # add messages from downloading inline-graphic files
    video_info_match_pattern = re.compile(
        r"WARNING elifecleaner:activity_AcceptedSubmissionPeerReviewImages:(.*?): (.*)"
    )
    for message in log_messages:
        message_parts = video_info_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if message_type in ["do_activity"]:
            comments.append(message_content)
    # add messages from adding version DOI
    version_doi_match_pattern = re.compile(
        r"WARNING elifecleaner:activity_AcceptedSubmissionVersionDoi:(.*?): (.*)"
    )
    for message in log_messages:
        message_parts = version_doi_match_pattern.search(message)
        if not message_parts:
            continue
        message_type = message_parts.group(1)
        message_content = message_parts.group(2)
        if message_type in [
            "do_activity",
        ]:
            comments.append(message_content)

    return comments


def production_comments_for_xml(log_content):
    "filter the log_content for those to go into the XML production-comments tag"
    log_messages = utils.unicode_encode(log_content).split("\n") if log_content else []
    filtered_messages = [
        line
        for line in log_messages
        if "WARNING elifecleaner:parse:check_art_file:" not in line
        and "INFO elifecleaner:parse:parse_article_xml:" not in line
        and "INFO elifecleaner:video:" not in line
        and "WARNING elifecleaner:activity_AcceptedSubmissionVersionDoi:" not in line
    ]
    return production_comments("\n".join(filtered_messages))


def set_article_id(xml_root, article_id, doi, version_doi):
    return prc.set_article_id(xml_root, article_id, doi, version_doi)


def set_volume(root, volume):
    return prc.set_volume(root, volume)


def modify_volume(xml_root, volume):
    "modify volume tag"
    if volume:
        set_volume(xml_root, volume)
    else:
        # remove volume tag
        article_meta_tag = xml_root.find(".//front/article-meta")
        if article_meta_tag:
            for tag in article_meta_tag.findall("volume"):
                article_meta_tag.remove(tag)


def set_elocation_id(root, elocation_id):
    return prc.set_elocation_id(root, elocation_id)


def clear_article_categories(xml_root):
    "remove tags in the article-categories tag"
    article_meta_tag = xml_root.find(".//front/article-meta")
    article_categories_tag = article_meta_tag.find(".//article-categories")
    if article_categories_tag is not None:
        # remove tags underneath it
        for tag in article_categories_tag.findall("*"):
            article_categories_tag.remove(tag)


def set_article_categories(xml_root, display_channel=None, article_categories=None):
    return prc.set_article_categories(xml_root, display_channel, article_categories)


def modify_article_categories(xml_root, display_channel=None, article_categories=None):
    "modify subj-group subject tags"
    clear_article_categories(xml_root)
    # remove the article-categories tag entirely if no data is to be addded
    if not display_channel and not article_categories:
        article_meta_tag = xml_root.find(".//front/article-meta")
        if article_meta_tag is not None:
            for tag in article_meta_tag.findall("article-categories"):
                article_meta_tag.remove(tag)
    else:
        set_article_categories(xml_root, display_channel, article_categories)


def set_permissions(xml_root, license_data_dict, copyright_year, copyright_holder):
    return prc.set_permissions(
        xml_root, license_data_dict, copyright_year, copyright_holder
    )


def clear_permissions(xml_root):
    "remove tags inside the permissions tag"
    article_meta_tag = xml_root.find(".//front/article-meta")
    permissions_tag = article_meta_tag.find("./permissions")
    if permissions_tag is not None:
        for tag in permissions_tag.findall("*"):
            permissions_tag.remove(tag)


def modify_permissions(xml_root, license_data_dict, copyright_year, copyright_holder):
    "modify the permissions tag including the license"
    clear_permissions(xml_root)
    set_permissions(xml_root, license_data_dict, copyright_year, copyright_holder)


def get_license_data(docmap_string, version_doi):
    "find the license from the docmap and return a dict of license data"
    license_url = license_from_docmap(
        docmap_string, version_doi=version_doi, identifier=version_doi
    )
    return license_data_by_url(license_url)


def get_copyright_year(history_data, doi):
    "get a copyright year from a list of history events otherwise use current year"
    first_version_published_date = published_date_from_history(history_data, doi)
    copyright_year = None
    # copyright year, from first version published, otherwise from the current datetime
    if first_version_published_date:
        copyright_year = time.strftime("%Y", first_version_published_date)
    else:
        copyright_year = datetime.strftime(utils.get_current_datetime(), "%Y")
    return copyright_year


def get_copyright_holder(xml_file_path):
    "from article XML populate copyright holder data"
    # generate copyright holder
    preprint_article, error_count = elifearticle_parse.build_article_from_xml(
        xml_file_path, detail="full"
    )
    return build.generate_copyright_holder(preprint_article.contributors)


def editor_contributors(docmap_string, version_doi):
    return prc.editor_contributors(docmap_string, version_doi)


def set_editors(parent, editors):
    return prc.set_editors(parent, editors)


def format_article_meta_xml(xml_root):
    "add whitespace around selected tags in XML article-meta"
    for tag in (
        xml_root.findall("./front/article-meta/article-id")
        + xml_root.findall("./front/article-meta/article-categories/subj-group")
        + xml_root.findall("./front/article-meta/article-categories/subj-group/subject")
        + xml_root.findall("./front/article-meta/volume")
        + xml_root.findall("./front/article-meta/history/date")
        + xml_root.findall("./front/article-meta/history/date/day")
        + xml_root.findall("./front/article-meta/history/date/month")
        + xml_root.findall("./front/article-meta/history/date/year")
        + xml_root.findall("./front/article-meta/pub-date")
        + xml_root.findall("./front/article-meta/pub-date/day")
        + xml_root.findall("./front/article-meta/pub-date/month")
        + xml_root.findall("./front/article-meta/pub-date/year")
        + xml_root.findall("./front/article-meta/pub-history")
        + xml_root.findall("./front/article-meta/pub-history/event")
        + xml_root.findall("./front/article-meta/pub-history/event/event-desc")
        + xml_root.findall("./front/article-meta/pub-history/event/date")
        + xml_root.findall("./front/article-meta/pub-history/event/date/day")
        + xml_root.findall("./front/article-meta/pub-history/event/date/month")
        + xml_root.findall("./front/article-meta/pub-history/event/date/year")
        + xml_root.findall("./front/article-meta/permissions/copyright-statement")
        + xml_root.findall("./front/article-meta/permissions/copyright-year")
        + xml_root.findall("./front/article-meta/permissions/copyright-holder")
        + xml_root.findall("./front/article-meta/permissions/license")
        + xml_root.findall(
            (
                "./front/article-meta/permissions/license/"
                "{http://www.niso.org/schemas/ali/1.0/}license_ref"
            )
        )
        + xml_root.findall("./front/article-meta/permissions/license/license-p")
        + xml_root.findall("./front/article-meta/contrib-group")
        + xml_root.findall("./front/article-meta/contrib-group/contrib")
        + xml_root.findall("./front/article-meta/contrib-group/contrib/name")
        + xml_root.findall("./front/article-meta/contrib-group/contrib/name/surname")
        + xml_root.findall(
            "./front/article-meta/contrib-group/contrib/name/given-names"
        )
        + xml_root.findall("./front/article-meta/contrib-group/contrib/role")
        + xml_root.findall("./front/article-meta/contrib-group/contrib/aff")
        + xml_root.findall(
            "./front/article-meta/contrib-group/contrib/aff/institution-wrap"
        )
        + xml_root.findall(
            "./front/article-meta/contrib-group/contrib/aff/institution-wrap/institution"
        )
        + xml_root.findall("./front/article-meta/contrib-group/contrib/aff/country")
    ):
        sub_article.tag_new_line_wrap(tag)
    for tag in (
        xml_root.findall("./front/article-meta/pub-history/event/self-uri")
        + xml_root.findall(
            "./front/article-meta/permissions/{http://www.niso.org/schemas/ali/1.0/}free_to_read"
        )
        + xml_root.findall("./front/article-meta/contrib-group/contrib/aff/addr-line")
    ):
        sub_article.tag_new_line_wrap_tail(tag)
