from elifecrossref import generate


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
