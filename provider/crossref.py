from elifecrossref import generate
from elifecrossref.conf import raw_config, parse_raw_config


def elifecrossref_config(settings):
    "parse the config values from the elifecrossref config"
    return parse_raw_config(raw_config(
        settings.elifecrossref_config_section,
        settings.elifecrossref_config_file))


def parse_article_xml(article_xml_files, tmp_dir):
    """Given a list of article XML files, parse into objects"""
    articles = []
    generate.TMP_DIR = tmp_dir
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
