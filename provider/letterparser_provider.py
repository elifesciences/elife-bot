"functions shared by letterparser related activities"

import os
import docker
from letterparser import generate, parse, zip_lib
from letterparser.conf import raw_config, parse_raw_config
import log


IDENTITY = "process_%s" % os.getpid()
LOGGER = log.logger("letterparser_provider.log", 'INFO', IDENTITY, loggerName=__name__)


ARTICLES_MIN_COUNT = 2


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
