import os
import shutil
import dateutil.parser
from collections import OrderedDict
from elifetools import xmlio
from provider import utils, lax_provider
from provider.storage_provider import storage_context
from provider.article_structure import ArticleInfo, file_parts

"""
Functions for processing article zip and XML for reuse by different activities
Originally refactoring them from the PMCDeposit activity for reuse into FTPArticle
"""

def list_dir(dir_name):
    dir_list = os.listdir(dir_name)
    dir_list = [dir_name + os.sep + item for item in dir_list]
    return dir_list


def file_list(dir_name):
    dir_list = list_dir(dir_name)
    return [item for item in dir_list if os.path.isfile(item)]


def file_name_from_name(file_name):
    name = file_name.split(os.sep)[-1]
    return name


def file_extension(file_name):
    name = file_name_from_name(file_name)
    if name:
        if len(name.split('.')) > 1:
            return name.split('.')[-1]
    return None


def stripped_file_name_map(file_names, logger=None):
    "from a list of file names, build a map of old to new file name with the version removed"
    file_name_map = OrderedDict()
    for df in file_names:
        filename = df.split(os.sep)[-1]
        info = ArticleInfo(filename)
        prefix, extension = file_parts(filename)
        if info.versioned is True and info.version is not None:
            # Use part before the -v number
            part_without_version = prefix.split('-v')[0]
        else:
            # Not a versioned file, use the whole file prefix
            part_without_version = prefix
        renamed_filename = '.'.join([part_without_version, extension])
        if renamed_filename:
            file_name_map[filename] = renamed_filename
        else:
            if logger:
                logger.info('there is no renamed file for ' + filename)
    return file_name_map


def rename_files_remove_version_number(files_dir, output_dir, logger=None):
    """Rename files to not include the version number, if present"""

    # Get a list of all files
    dirfiles = file_list(files_dir)

    file_name_map = stripped_file_name_map(dirfiles, logger)

    for old_name, new_name in list(file_name_map.items()):
        if new_name is not None:
            shutil.move(files_dir + os.sep + old_name, output_dir + os.sep + new_name)

    return file_name_map


def convert_xml(xml_file, file_name_map):

    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file,
        return_doctype_dict=True,
        return_processing_instructions=True)

    # Convert xlink href values
    total = xmlio.convert_xlink_href(root, file_name_map)
    # TODO - compare whether all file names were converted

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions)

    f = open(xml_file, 'wb')
    f.write(reparsed_string)
    f.close()


def verify_rename_files(file_name_map):
    """
    Each file name as key should have a non None value as its value
    otherwise the file did not get renamed to something new and the
    rename file process was not complete
    """
    verified = True
    renamed_list = []
    not_renamed_list = []
    for k, v in list(file_name_map.items()):
        if v is None:
            verified = False
            not_renamed_list.append(k)
        else:
            renamed_list.append(k)

    return (verified, renamed_list, not_renamed_list)


def new_pmc_zip_filename(journal, volume, fid, revision=None):
    filename = journal
    filename = filename + '-' + utils.pad_volume(volume)
    filename = filename + '-' + utils.pad_msid(fid)
    if revision:
        filename = filename + '.r' + str(revision)
    filename += '.zip'
    return filename


def latest_archive_zip_revision(doi_id, s3_keys, journal, status):
    """
    Get the most recent version of the article zip file from the
    list of bucket key names
    """
    s3_key_name = None

    name_prefix_to_match = (journal + '-' + utils.pad_msid(doi_id)
                            + '-' + status + '-v')

    highest = 0
    for key in s3_keys:
        if key["name"].startswith(name_prefix_to_match):
            version_and_date = None
            try:
                parts = key["name"].split(name_prefix_to_match)
                version = parts[1].split('-')[0]
                date_formatted = dateutil.parser.parse(key["last_modified"])
                date_part = date_formatted.strftime(utils.S3_DATE_FORMAT)
                version_and_date = int(version + date_part)
            except:
                pass
            if version_and_date and version_and_date > highest:
                s3_key_name = key["name"]
                highest = version_and_date

    return s3_key_name


def download_article_xml(settings, to_dir, bucket_folder, bucket_name, version=None):
    xml_file = lax_provider.get_xml_file_name(
        settings, bucket_folder, bucket_name, version)
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/" + bucket_folder
    # download the file
    article_xml_filename = xml_file.split("/")[-1]
    filename_plus_path = os.path.join(to_dir, article_xml_filename)
    with open(filename_plus_path, "wb") as open_file:
        storage_resource_origin = orig_resource + "/" + article_xml_filename
        storage.get_resource_to_file(storage_resource_origin, open_file)
        return filename_plus_path


def download_jats(settings, expanded_folder_name, to_dir, logger):
    """download the jats file from the expanded folder on S3"""
    jats_file = None
    expanded_bucket_name = (
        settings.publishing_buckets_prefix + settings.expanded_bucket)
    try:
        jats_file = download_article_xml(
            settings, to_dir, expanded_folder_name, expanded_bucket_name)
    except Exception as exception:
        logger.exception(
            "Exception downloading jats from from expanded folder %s. Details: %s" %
            (str(expanded_folder_name), str(exception)))
    return jats_file
