import os
import shutil
import zipfile
import glob
from collections import OrderedDict
from xml.etree.ElementTree import Element
import dateutil.parser
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
        if len(name.split(".")) > 1:
            return name.split(".")[-1]
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
            part_without_version = prefix.split("-v")[0]
        else:
            # Not a versioned file, use the whole file prefix
            part_without_version = prefix
        renamed_filename = ".".join([part_without_version, extension])
        if renamed_filename:
            file_name_map[filename] = renamed_filename
        else:
            if logger:
                logger.info("there is no renamed file for " + filename)
    return file_name_map


def rename_files_remove_version_number(files_dir, output_dir, logger=None):
    """Rename files to not include the version number, if present"""

    # Get a list of all files
    dirfiles = sorted(file_list(files_dir))

    file_name_map = stripped_file_name_map(dirfiles, logger)

    for old_name, new_name in list(file_name_map.items()):
        if new_name is not None:
            shutil.move(files_dir + os.sep + old_name, output_dir + os.sep + new_name)

    return file_name_map


def convert_xml(xml_file, file_name_map):

    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    # Convert xlink href values
    total = xmlio.convert_xlink_href(root, file_name_map)
    # TODO - compare whether all file names were converted

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)


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
    filename = filename + "-" + utils.pad_volume(volume)
    filename = filename + "-" + utils.pad_msid(fid)
    if revision:
        filename = filename + ".r" + str(revision)
    filename += ".zip"
    return filename


def latest_archive_zip_revision(doi_id, s3_keys, journal, status):
    """
    Get the most recent version of the article zip file from the
    list of bucket key names
    """
    s3_key_name = None

    name_prefix_to_match = journal + "-" + utils.pad_msid(doi_id) + "-" + status + "-v"

    highest = 0
    for key in s3_keys:
        if key["name"].startswith(name_prefix_to_match):
            version_and_date = None
            try:
                parts = key["name"].split(name_prefix_to_match)
                version = parts[1].split("-")[0]
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
        settings, bucket_folder, bucket_name, version
    )
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
    expanded_bucket_name = settings.publishing_buckets_prefix + settings.expanded_bucket
    try:
        jats_file = download_article_xml(
            settings, to_dir, expanded_folder_name, expanded_bucket_name
        )
    except Exception as exception:
        logger.exception(
            "Exception downloading jats from from expanded folder %s. Details: %s"
            % (str(expanded_folder_name), str(exception))
        )
    return jats_file


def unzip_article_xml(input_zip_file_path, output_dir):
    "unzip the article XML file from an article zip file"
    article_xml_path = None
    with zipfile.ZipFile(input_zip_file_path, "r") as open_zipfile:
        for zipfile_info in open_zipfile.infolist():
            if zipfile_info.filename.endswith(".xml"):
                info = ArticleInfo(file_name_from_name(zipfile_info.filename))
                if info.file_type == "ArticleXML":
                    article_xml_path = open_zipfile.extract(zipfile_info, output_dir)
                    break
    return article_xml_path


def repackage_archive_zip_to_pmc_zip(
    input_zip_file_path,
    new_zip_file_path,
    temp_dir,
    logger,
    alter_xml=False,
    remove_version_doi=False,
    retain_version_number=False,
    convert_history_events=False,
):
    "repackage the zip file  to a PMC zip format"
    # make temporary directories
    zip_extracted_dir = os.path.join(temp_dir, "junk_dir")
    os.makedirs(zip_extracted_dir, exist_ok=True)
    zip_renamed_files_dir = os.path.join(temp_dir, "rename_dir")
    os.makedirs(zip_renamed_files_dir, exist_ok=True)
    # unzip contents
    archive_zip_name = input_zip_file_path
    with zipfile.ZipFile(archive_zip_name, "r") as myzip:
        myzip.extractall(zip_extracted_dir)

    if retain_version_number:
        # do not change the file names
        logger.info(
            "not removing version number in files from %s"
            % (input_zip_file_path.rsplit(os.sep, 1)[-1])
        )
        expanded_files_dir = zip_extracted_dir
        # create file name map with unchanged file names
        dirfiles = sorted(file_list(expanded_files_dir))
        file_name_map = OrderedDict()
        for df in dirfiles:
            filename = df.split(os.sep)[-1]
            file_name_map[filename] = filename
    else:
        # rename the files and profile the files
        file_name_map = rename_files_remove_version_number(
            files_dir=zip_extracted_dir, output_dir=zip_renamed_files_dir
        )
        # verify file names
        (verified, renamed_list, not_renamed_list) = verify_rename_files(file_name_map)
        logger.info(
            "repackage_archive_zip_to_pmc_zip() verified renamed files from %s: %s"
            % (input_zip_file_path.rsplit(os.sep, 1)[-1], verified)
        )
        if renamed_list:
            logger.info("renamed: %s" % sorted(renamed_list))
        if not_renamed_list:
            logger.info("not renamed: %s" % sorted(not_renamed_list))
        expanded_files_dir = zip_renamed_files_dir

    logger.info("file_name_map: %s" % file_name_map)

    # convert the XML
    article_xml_file = glob.glob(expanded_files_dir + "/*.xml")[0]
    if alter_xml:
        # Temporary XML rewrite of related-object tag
        alter_xml_related_object(article_xml_file, logger)
    if remove_version_doi:
        # remove the version DOI article-id tag
        remove_version_doi_tag(article_xml_file, logger)
    if convert_history_events:
        # add related-article tags for each history event
        convert_history_event_tags(article_xml_file, logger)
    convert_xml(xml_file=article_xml_file, file_name_map=file_name_map)
    # rezip the files into PMC zip format
    logger.info("creating new PMC zip file named " + new_zip_file_path)
    with zipfile.ZipFile(
        new_zip_file_path,
        "w",
        zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as new_zipfile:
        dirfiles = file_list(expanded_files_dir)
        for dir_file in dirfiles:
            filename = dir_file.split(os.sep)[-1]
            new_zipfile.write(dir_file, filename)
    return True


def alter_xml_related_object(xml_file, logger):
    "modify the related-object tag in the article XML file"
    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    # Convert related-object tag
    for xml_tag in root.findall("./sub-article/front-stub/related-object"):
        logger.info("Converting related-object tag to ext-link tag in sub-article")
        xml_tag.tag = "ext-link"
        xml_tag.set("ext-link-type", "uri")
        # delete attributes
        for attribute_name in ["link-type", "object-id", "object-id-type"]:
            if xml_tag.attrib.get(attribute_name):
                del xml_tag.attrib[attribute_name]

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)


def remove_version_doi_tag(xml_file, logger):
    "remove the version DOI article-id tag from the article XML file"
    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    # Convert related-object tag
    article_meta_tag = root.find("./front/article-meta")
    if article_meta_tag:
        for xml_tag in article_meta_tag.findall('article-id[@pub-id-type="doi"]'):
            if xml_tag.get("specific-use") and xml_tag.get("specific-use") == "version":
                logger.info("Removing version DOI article-id tag")
                article_meta_tag.remove(xml_tag)

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)


def convert_history_event_tags(xml_file, logger):
    "for each preprint event tag in pub-history add a related-article tag"
    # Register namespaces
    xmlio.register_xmlns()

    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file, return_doctype_dict=True, return_processing_instructions=True
    )

    #
    article_meta_tag = root.find("./front/article-meta")
    if article_meta_tag:
        event_index = 1
        for event_tag in article_meta_tag.findall("pub-history/event"):
            for self_uri_tag in event_tag.findall("self-uri"):
                if self_uri_tag.get("content-type") in [
                    "preprint",
                    "reviewed-preprint",
                ] and self_uri_tag.get("{http://www.w3.org/1999/xlink}href"):
                    # add a related-article tag
                    doi_value = utils.doi_uri_to_doi(
                        self_uri_tag.get("{http://www.w3.org/1999/xlink}href")
                    )
                    if "http://" in doi_value or "https://" in doi_value:
                        # the value is not a DOI, do not add a related-article tag for it
                        continue
                    logger.info(
                        "Adding a related-article tag for event self-uri %s"
                        % self_uri_tag.get("{http://www.w3.org/1999/xlink}href")
                    )
                    related_article_tag = Element("related-article")
                    related_article_tag.set("ext-link-type", "doi")
                    related_article_tag.set("id", "hra%s" % event_index)
                    related_article_tag.set("related-article-type", "preprint")
                    related_article_tag.set(
                        "{http://www.w3.org/1999/xlink}href", doi_value
                    )
                    # find the index of the abstract tag for where to insert the tag
                    abstract_tag_index = 0
                    for tag_index, meta_tag in enumerate(
                        article_meta_tag.iterfind("*")
                    ):
                        if meta_tag.tag == "abstract":
                            abstract_tag_index = tag_index
                            logger.info(
                                "Found abstract tag at index %s" % abstract_tag_index
                            )
                            break
                    # insert the tag directly prior to the abstract tag
                    article_meta_tag.insert(abstract_tag_index, related_article_tag)

                    event_index += 1

    # Start the file output
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)


def zip_files(zip_file_path, folder_path, caller_name, logger):
    "add files from folder_name to zip, preserving subfolder names"
    with zipfile.ZipFile(
        zip_file_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as open_zipfile:
        for root, dirs, files in os.walk(folder_path):
            for dir_file in files:
                filename = os.path.join(root, dir_file)
                if os.path.isfile(filename):
                    logger.info(
                        "%s, adding file %s to zip file %s",
                        caller_name,
                        filename,
                        zip_file_path,
                    )
                    # Archive file name, effectively strip the local folder name
                    arcname = root.rsplit(folder_path, 1)[-1] + "/" + dir_file
                    open_zipfile.write(filename, arcname)
