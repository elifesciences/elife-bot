"functions shared by letterparser related activities"

import os
from collections import OrderedDict
import docker
from letterparser import generate, parse, zip_lib
from letterparser.conf import raw_config, parse_raw_config
import log


IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("letterparser_provider.log", 'INFO', IDENTITY, loggerName=__name__)


ARTICLES_MIN_COUNT = 2

ARTICLE_TITLE_MAP = [
    OrderedDict([
        ('snippet', 'decision letter'),
        ('min_count', 1)
    ]),
    OrderedDict([
        ('snippet', 'author response'),
        ('min_count', 1)
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


def process_zip(file_name, config, temp_dir, logger=LOGGER):
    """one-step processing of decision letter zip into article objects and assets"""
    statuses = {}
    # Unzip file
    statuses["unzip"], docx_file_name, asset_file_names = unzip_zip(
        file_name, temp_dir, logger=logger)
    # Convert docx to articles
    statuses["build"], articles = docx_to_articles(
        docx_file_name, config=config, logger=logger)
    # Validate content of articles
    statuses["valid"], error_messages = validate_articles(
        articles, logger=logger)
    return articles, asset_file_names, statuses, error_messages


def process_articles_to_xml(articles, temp_dir, logger=LOGGER, pretty=True, indent=""):
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


def docx_to_articles(file_name, root_tag="root", config=None, logger=LOGGER):
    try:
        return True, generate.docx_to_articles(file_name, root_tag, config)
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


def output_bucket_folder_name(settings, manuscript):
    return settings.decision_letter_bucket_folder_name_pattern.format(manuscript=manuscript)


def output_xml_file_name(settings, manuscript):
    return settings.decision_letter_xml_file_name_pattern.format(manuscript=manuscript)
