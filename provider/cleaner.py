import os
import logging
import re
from elifecleaner import (
    LOGGER,
    configure_logging,
    parse,
    transform,
    video,
    video_xml,
    zip_lib,
)
from provider import utils
from provider.storage_provider import storage_context

LOG_FILENAME = "elifecleaner.log"
LOG_FORMAT_STRING = (
    "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
)


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


def rezip(asset_file_name_map, output_dir, zip_file_name):
    return transform.rezip(asset_file_name_map, output_dir, zip_file_name)


def video_data_from_files(files, article_id):
    return video.video_data_from_files(files, article_id)


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
    return comments
