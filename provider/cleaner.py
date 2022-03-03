import logging
import re
from elifecleaner import LOGGER, configure_logging, parse, transform, zip_lib
from provider.storage_provider import storage_context

LOG_FILENAME = "elifecleaner.log"


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


def bucket_asset_file_name_map(settings, bucket_name, expanded_folder):
    "list of bucket objects in the expanded_folder and return a map of object to its S3 path"
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/" + expanded_folder
    s3_key_names = storage.list_resources(orig_resource)
    return {key_name: orig_resource + "/" + key_name for key_name in s3_key_names}
