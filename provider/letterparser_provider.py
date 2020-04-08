"functions shared by letterparser related activities"

import os
from collections import OrderedDict
import zipfile
import docker
from elifetools import parseJATS as parser
from letterparser import generate, parse, zip_lib
from letterparser.conf import raw_config, parse_raw_config
from letterparser.utils import manuscript_from_file_name
import log


IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("letterparser_provider.log", 'INFO', IDENTITY, loggerName=__name__)


ARTICLES_MIN_COUNT = 1

ARTICLE_TITLE_MAP = [
    OrderedDict([
        ('snippet', 'decision letter'),
        ('min_count', 0)
    ]),
    OrderedDict([
        ('snippet', 'author response'),
        ('min_count', 0)
    ])
]


def letterparser_config(settings):
    """parse the config values from letterparser.cfg"""
    return parse_raw_config(raw_config(
        settings.letterparser_config_section,
        settings.letterparser_config_file))


def parse_file(file_name, config):
    try:
        return parse.parse_file(file_name, config)
    except docker.errors.APIError:
        LOGGER.info('Error connecting to docker')
        raise


def check_input(file_name):
    """check the input zip file complies with the expected naming and structure"""
    error_messages = []
    # check file_name exists
    if not file_name:
        error_messages.append('File %s does not exist' % file_name)
    # check file name
    if file_name and not file_name.endswith('.zip'):
        error_messages.append('File %s name does not end in .zip' % file_name)
    # check file is a valid zip
    if file_name and not zipfile.is_zipfile(file_name):
        error_messages.append('File %s is not a valid zip file' % file_name)
    # profile the zip using letterparser library to check for .docx file
    zip_docx_info = None
    if file_name and zipfile.is_zipfile(file_name):
        zip_docx_info, zip_asset_infos = zip_lib.profile_zip(file_name)
        if not zip_docx_info:
            error_messages.append('Could not find .docx file in zip file %s' % file_name)
        # provide additional hint whether a docx file is in a subfolder
        with zipfile.ZipFile(file_name, 'r') as open_zipfile:
            for zipfile_info in open_zipfile.infolist():
                zipfile_file = zipfile_info.filename
                if (
                        zipfile_file.endswith('.docx')
                        and not zipfile_file.startswith('__MACOSX/')
                        and '/' in zipfile_file):
                    error_messages.append(
                        'Note: .docx file %s may be in a subfolder in zip file %s' %
                        (zipfile_file, file_name))
    # check manuscript can be extracted from the docx file name
    if zip_docx_info and not manuscript_from_file_name(zip_docx_info.filename):
        error_messages.append(
            'Cannot get manuscript ID from %s inside %s' %
            (zip_docx_info.filename, file_name))

    return error_messages


def process_zip(file_name, config, temp_dir, logger=LOGGER):
    """one-step processing of decision letter zip into article objects and assets"""
    statuses = {}
    # Unzip file
    statuses["unzip"], docx_file_name, asset_file_names = unzip_zip(
        file_name, temp_dir, logger=logger)
    # Convert docx to articles
    statuses["build"], articles = docx_to_articles(
        docx_file_name, temp_dir, config=config, logger=logger)
    # Validate content of articles
    statuses["valid"], error_messages = validate_articles(
        articles, logger=logger)
    return articles, asset_file_names, statuses, error_messages


def process_articles_to_xml(articles, temp_dir, logger=LOGGER, pretty=False, indent=""):
    """convert decision letter Article objects to XML"""
    statuses = {}
    # Generate XML from articles
    statuses["generate"], root = generate_root(articles, temp_dir=temp_dir, logger=logger)
    # Output XML
    statuses["output"], xml_string = output_xml(root, pretty=pretty, indent=indent, logger=logger)
    return xml_string, statuses


def unzip_zip(file_name, temp_dir, logger=LOGGER):
    try:
        docx_file_name, asset_file_names = zip_lib.unzip_zip(file_name, temp_dir)
        return True, docx_file_name, asset_file_names
    except:
        logger.info('Error unzipping file %s' % file_name)
    return False, None, []


def docx_to_articles(file_name, temp_dir, root_tag="root", config=None, logger=LOGGER):
    try:
        return True, generate.docx_to_articles(file_name, root_tag, config, temp_dir)
    except:
        logger.info('Error converting file %s to articles' % file_name)
    return False, None


def validate_articles(articles, logger=LOGGER):
    """check articles for values we expect to make them valid"""
    error_messages = []
    valid = True

    # check for any articles at all
    if not articles:
        valid = False
        error_message = 'No articles to check'
        error_messages.append('No articles to check')
        logger.info(error_message)

    # check for two article objects
    if articles and len(articles) < ARTICLES_MIN_COUNT:
        valid = False
        error_message = 'Only {count} articles, expected at least {min}'.format(
            count=len(articles), min=ARTICLES_MIN_COUNT)
        error_messages.append(error_message)
        logger.info(error_message)

    # check for article titles
    if articles:
        for article_title_match in ARTICLE_TITLE_MAP:
            matched_articles = [
                article for article in articles
                if article.title and article_title_match.get('snippet') in article.title.lower()]
            if len(matched_articles) < article_title_match.get('min_count'):
                valid = False
                error_message = 'Only {count} {snippet} articles, expected at least {min}'.format(
                    count=len(matched_articles),
                    snippet=article_title_match.get('snippet'),
                    min=ARTICLES_MIN_COUNT)
                error_messages.append(error_message)
                logger.info(error_message)

    # check each article has a DOI
    if articles:
        for i, article in enumerate(articles):
            if not article.doi:
                valid = False
                error_message = 'Article {i} is missing a DOI'.format(i=i)
                error_messages.append(error_message)
                logger.info(error_message)

    return valid, error_messages


def generate_root(articles, root_tag="root", temp_dir="tmp", logger=LOGGER):
    try:
        return True, generate.generate(articles, root_tag, temp_dir)
    except:
        logger.info('Error generating XML from articles')
    return False, None


def output_xml(root, pretty=False, indent="", logger=LOGGER):
    try:
        return True, generate.output_xml(root, pretty, indent)
    except:
        logger.info('Error generating output XML from ElementTree root element')
    return False, None


def manuscript_from_articles(articles):
    """from a list of articles return a manuscript value"""
    if articles:
        return articles[0].manuscript
    return None


def article_doi_from_xml(xml_string):
    """get main article DOI from XML string"""
    doi = None
    xml = parser.parse_xml(xml_string)
    article_ids = parser.article_id_list(xml)
    if article_ids:
        first_article_id = article_ids[0]
        article_id = first_article_id.get('value')
        doi = '.'.join(article_id.split('.')[0:-1])
    return doi


def output_bucket_folder_name(settings, manuscript):
    return settings.decision_letter_bucket_folder_name_pattern.format(manuscript=manuscript)


def output_xml_file_name(settings, manuscript):
    return settings.decision_letter_xml_file_name_pattern.format(manuscript=manuscript)
