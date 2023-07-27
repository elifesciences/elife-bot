import os
import json
import logging
import re
from urllib.parse import urlparse
from xml.etree.ElementTree import SubElement
import requests
from docmaptools import parse as docmap_parse
from elifecleaner import (
    LOGGER,
    assessment_terms,
    configure_logging,
    fig,
    parse,
    prc,
    sub_article,
    transform,
    video,
    video_xml,
    zip_lib,
)
from provider import utils
from provider.storage_provider import storage_context
from provider.article_processing import file_extension

LOG_FILENAME = "elifecleaner.log"
LOG_FORMAT_STRING = (
    "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
)

# March 2023 temporary config to not send emails for particular test files
PRC_INGEST_IGNORE_SEND_EMAIL = [
    "02-28-2023-RA-RP-eLife-84747.zip",
    "18-05-2021-RA-RP-eLife-70493.zip",
    "22-04-2022-RA-RP-eLife-79713.zip",
]

# March 2023 for testing an article which appears in Sciety docmaps but not in Data Hub docmaps
SCIETY_DOCMAP_URL_PATTERN = (
    "https://sciety.org/docmaps/v1/evaluations-by/elife/{doi}.docmap.json"
)

# March 2023 for testing an article which appears in Sciety docmaps but not in Data Hub docmaps
SCIETY_TEST_PREPRINT_DICT = {"70493": "10.1101/2021.06.02.446694"}

REQUESTS_TIMEOUT = 10


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
    prc.transform_elocation_id(root, identifier=identifier)
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
    return fig.is_p_inline_graphic(tag, sub_article_id, p_tag_index, identifier)


def inline_graphic_tags(xml_file_path):
    "get the inline-graphic tags from an XML file"
    root = parse_article_xml(xml_file_path)
    tags = []
    # find tags in the XML
    for inline_graphic_tag in root.findall(".//inline-graphic"):
        tags.append(inline_graphic_tag)
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
    root = parse_article_xml(xml_file_path)

    for href, new_file_name in href_to_file_name_map.items():
        for inline_graphic_tag in root.findall(
            ".//inline-graphic[@{http://www.w3.org/1999/xlink}href='%s']" % href
        ):
            if tag_xlink_href(inline_graphic_tag) == href:
                inline_graphic_tag.set(
                    "{http://www.w3.org/1999/xlink}href", new_file_name
                )
    # write XML file to disk
    write_xml_file(root, xml_file_path, identifier)


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


def transform_fig(sub_article_root, identifier):
    "transform inline-graphic tags into fig tags"
    return fig.transform_fig(sub_article_root, identifier)


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
    root = parse_article_xml(xml_file_path)
    add_file_tags(root, file_detail_list)
    # write XML file to disk
    write_xml_file(root, xml_file_path, identifier)


def docmap_url(settings, article_id):
    "URL of the preprint docmap endpoint"
    # temporarily use a different docmap for a test test article
    if article_id in SCIETY_TEST_PREPRINT_DICT.keys():
        return SCIETY_DOCMAP_URL_PATTERN.format(
            doi=SCIETY_TEST_PREPRINT_DICT.get(article_id)
        )
    docmap_url_pattern = getattr(settings, "docmap_url_pattern", None)
    return (
        docmap_url_pattern.format(article_id=article_id) if docmap_url_pattern else None
    )


def add_sub_article_xml(docmap_string, article_xml, terms_yaml=None):
    if terms_yaml:
        # set the path to the YAML file containing assessment terms data
        assessment_terms.ASSESSMENT_TERMS_YAML = terms_yaml
    return sub_article.add_sub_article_xml(docmap_string, article_xml)


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


def url_exists(url, logger):
    "check if URL exists and is successful status code"
    exists = False
    response = requests.get(url, timeout=REQUESTS_TIMEOUT)
    if 200 <= response.status_code < 400:
        exists = True
    elif response.status_code >= 400:
        logger.info("Status code for %s was %s" % (url, response.status_code))
    return exists


def get_docmap(url):
    "GET request for the docmap json"
    response = requests.get(url, timeout=REQUESTS_TIMEOUT)
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


def get_docmap_by_account_id(url, account_id):
    "GET request for the docmap json and return the eLife docmap if a list is returned"
    content = get_docmap(url)
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


def review_date_from_docmap(docmap_string, input_filename):
    return prc.review_date_from_docmap(docmap_string, input_filename)


def date_struct_from_string(date_string):
    return prc.date_struct_from_string(date_string)


def add_history_date(root, date_type, date_struct, identifier):
    return prc.add_history_date(root, date_type, date_struct, identifier)


def docmap_preprint_history_from_docmap(docmap_string):
    d_json = docmap_parse.docmap_json(docmap_string)
    return docmap_parse.docmap_preprint_history(d_json)


def add_pub_history(root, history_data, identifier):
    return prc.add_pub_history(root, history_data, identifier)


def volume_from_docmap(docmap_string, input_filename):
    return prc.volume_from_docmap(docmap_string, input_filename)


def version_doi_from_docmap(docmap_string, input_filename):
    return prc.version_doi_from_docmap(docmap_string, input_filename)


def next_version_doi(version_doi, input_filename):
    return prc.next_version_doi(version_doi, input_filename)


def add_version_doi(xml_root, version_doi, input_filename):
    return prc.add_version_doi(xml_root, version_doi, input_filename)


def xml_rewrite_file_tags(xml_file_path, file_transformations, identifier):
    transform.xml_rewrite_file_tags(xml_file_path, file_transformations, identifier)


def write_xml_file(root, xml_asset_path, identifier):
    transform.write_xml_file(root, xml_asset_path, identifier)


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
