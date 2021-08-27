import os
import time
from collections import OrderedDict
import requests
from elifearticle.article import ArticleDate
from elifecrossref import generate
from elifecrossref.conf import raw_config, parse_raw_config
from provider import article_processing, lax_provider, utils
from provider.storage_provider import storage_context


def override_tmp_dir(tmp_dir):
    """explicit override of TMP_DIR in the generate module"""
    if tmp_dir:
        generate.TMP_DIR = tmp_dir


def elifecrossref_config(settings):
    "parse the config values from the elifecrossref config"
    return parse_raw_config(raw_config(
        settings.elifecrossref_config_section,
        settings.elifecrossref_config_file))


def parse_article_xml(article_xml_files, tmp_dir=None):
    """Given a list of article XML files, parse into objects"""
    override_tmp_dir(tmp_dir)
    articles = []
    # convert one file at a time
    for article_xml in article_xml_files:
        article_list = None
        try:
            # Convert the XML file as a list to a list of article objects
            article_list = generate.build_articles([article_xml])
        except:
            continue
        if article_list:
            articles.append(article_list[0])
    return articles


def article_xml_list_parse(article_xml_files, bad_xml_files, tmp_dir=None):
    """given a list of article XML file names parse to an article object map"""
    article_object_map = OrderedDict()
    # parse one at a time to check which parse and which are bad
    for xml_file in article_xml_files:
        articles = parse_article_xml([xml_file], tmp_dir)
        if articles:
            article_object_map[xml_file] = articles[0]
        else:
            bad_xml_files.append(xml_file)
    return article_object_map


def set_article_pub_date(article, crossref_config, settings, logger):
    """if there is no pub date then set it from lax data"""
    # Check for a pub date
    article_pub_date = article_first_pub_date(crossref_config, article)
    # if no date was found then look for one on Lax
    if not article_pub_date:
        lax_pub_date = lax_provider.article_publication_date(
            article.manuscript, settings, logger)
        if lax_pub_date:
            date_struct = time.strptime(lax_pub_date, utils.S3_DATE_FORMAT)
            pub_date_object = ArticleDate(
                crossref_config.get('pub_date_types')[0], date_struct)
            article.add_date(pub_date_object)


def set_article_version(article, settings):
    """if there is no version then set it from lax data"""
    if not article.version:
        lax_version = lax_provider.article_highest_version(
            article.manuscript, settings)
        if lax_version:
            article.version = lax_version


def article_first_pub_date(crossref_config, article):
    "find the first article pub date from the list of crossref config pub_date_types"
    pub_date = None
    if crossref_config.get('pub_date_types'):
        # check for any useable pub date
        for pub_date_type in crossref_config.get('pub_date_types'):
            if article.get_date(pub_date_type):
                pub_date = article.get_date(pub_date_type)
                break
    return pub_date


def approve_to_generate(crossref_config, article):
    """
    Given an article object, decide if crossref deposit should be
    generated from it
    """
    approved = None
    # Embargo if the pub date is in the future
    article_pub_date = article_first_pub_date(crossref_config, article)
    if article_pub_date:
        now_date = time.gmtime()
        # if Pub date is later than now, do not approve
        approved = bool(article_pub_date.date < now_date)
    else:
        # No pub date, then we approve it
        approved = True

    return approved


def approve_to_generate_list(article_object_map, crossref_config, bad_xml_files):
    """decide which article objects are suitable to generate Crossref deposits"""
    generate_article_object_map = OrderedDict()
    for xml_file, article in list(article_object_map.items()):
        if approve_to_generate(crossref_config, article):
            generate_article_object_map[xml_file] = article
        else:
            bad_xml_files.append(xml_file)
    return generate_article_object_map


def crossref_data_payload(crossref_login_id, crossref_login_passwd, operation='doMDUpload'):
    """assemble a requests data payload for Crossref endpoint"""
    return {
        'operation': operation,
        'login_id': crossref_login_id,
        'login_passwd': crossref_login_passwd
    }


def upload_files_to_endpoint(url, payload, xml_files):
    """Using an HTTP POST, deposit the file to the Crossref endpoint"""

    # Default return status
    status = True
    http_detail_list = []

    for xml_file in xml_files:
        files = {'file': open(xml_file, 'rb')}

        response = requests.post(url, data=payload, files=files)

        # Check for good HTTP status code
        if response.status_code != 200:
            status = False
        # print response.text
        http_detail_list.append("XML file: " + xml_file)
        http_detail_list.append("HTTP status: " + str(response.status_code))
        http_detail_list.append("HTTP response: " + response.text)

    return status, http_detail_list


def generate_crossref_xml_to_disk(article_object_map, crossref_config, good_xml_files,
                                  bad_xml_files, submission_type="journal",
                                  pretty=False, indent=""):
    """from the article object generate crossref deposit XML"""
    for xml_file, article in list(article_object_map.items()):
        try:
            # Will write the XML to the TMP_DIR
            generate.crossref_xml_to_disk(
                [article], crossref_config, submission_type=submission_type,
                pretty=pretty, indent=indent)
            # Add filename to the list of good files
            good_xml_files.append(xml_file)
        except:
            # Add the file to the list of bad files
            bad_xml_files.append(xml_file)
    # Any files generated is a sucess, even if one failed
    return True


def get_to_folder_name(folder_name, date_stamp):
    """
    From the date_stamp
    return the S3 folder name to save published files into
    """
    return folder_name + date_stamp + "/"


def get_outbox_s3_key_names(settings, bucket_name, outbox_folder):
    """get a list of .xml S3 key names from the outbox"""
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = (
        storage_provider + bucket_name + "/" + outbox_folder.rstrip('/'))
    s3_key_names = storage.list_resources(orig_resource)
    # add back the outbox_folder to the key names
    full_s3_key_names = [(outbox_folder.rstrip('/') + '/' + key_name) for key_name in s3_key_names]
    # return only the .xml files
    return [key_name for key_name in full_s3_key_names if key_name.endswith('.xml')]


def download_files_from_s3_outbox(settings, bucket_name, outbox_s3_key_names, to_dir, logger):
    """from the s3 outbox folder,  download the .xml files"""
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/"

    for name in outbox_s3_key_names:
        # Download objects from S3 and save to disk
        file_name = name.split('/')[-1]
        file_path = os.path.join(to_dir, file_name)
        storage_resource_origin = orig_resource + '/' + name
        try:
            with open(file_path, 'wb') as open_file:
                logger.info("Downloading %s to %s" % (storage_resource_origin, file_path))
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except IOError:
            logger.exception("Failed to download file %s.", name)
            return False
    return True


def clean_outbox(settings, bucket_name, outbox_folder, to_folder, published_file_names):
    """Clean out the S3 outbox folder"""

    # Concatenate the expected S3 outbox file names
    s3_key_names = []
    for name in published_file_names:
        filename = name.split(os.sep)[-1]
        s3_key_name = outbox_folder + filename
        s3_key_names.append(s3_key_name)

    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"

    for name in s3_key_names:
        # Do not delete the from_folder itself, if it is in the list
        if name == outbox_folder:
            continue
        filename = name.split("/")[-1]
        new_s3_key_name = to_folder + filename

        orig_resource = storage_provider + bucket_name + "/" + name
        dest_resource = storage_provider + bucket_name + "/" + new_s3_key_name

        # First copy
        storage.copy_resource(orig_resource, dest_resource)

        # Then delete the old key if successful
        storage.delete_resource(orig_resource)


def upload_crossref_xml_to_s3(settings, bucket_name, to_folder, file_names):
    """
    Upload a copy of the crossref XML to S3 for reference
    """
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"

    for file_name in file_names:
        resource_dest = (
            storage_provider + bucket_name + "/" + to_folder +
            article_processing.file_name_from_name(file_name))
        storage.set_resource_from_filename(resource_dest, file_name)


def doi_exists(doi, logger):
    """given a DOI check if it exists in Crossref"""
    exists = False
    doi_url = utils.get_doi_url(doi)
    response = requests.head(doi_url)
    if 300 <= response.status_code < 400:
        exists = True
    elif response.status_code < 300 or response.status_code >= 500:
        logger.info('Status code for %s was %s' % (doi, response.status_code))
    return exists
