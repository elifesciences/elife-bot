import time
import requests
from elifearticle.article import ArticleDate
from elifecrossref import generate
from elifecrossref.conf import raw_config, parse_raw_config
from provider import lax_provider, utils


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
