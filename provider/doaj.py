import time
from collections import OrderedDict


LINK_URL_PATTERN = "https://elifesciences.org/articles/%s"
EISSN = "2050-084X"


def doaj_json(article_json):
    doaj_json = OrderedDict()
    doaj_json["bibjson"] = bibjson(article_json)
    return doaj_json


def bibjson(article_json):
    bibjson = OrderedDict()
    bibjson["abstract"] = abstract(article_json.get("abstract", {}))
    bibjson["author"] = author(article_json.get("authors", []))
    bibjson["identifier"] = identifier(article_json)
    bibjson["journal"] = journal(article_json)
    bibjson["keywords"] = keywords(article_json.get("keywords", []))
    bibjson["link"] = link(article_json)
    published_date = time.strptime(article_json["published"], "%Y-%m-%dT%H:%M:%SZ")
    bibjson["month"] = month(published_date)
    bibjson["title"] = title(article_json)
    bibjson["year"] = year(published_date)
    return bibjson


def abstract(abstract_json):
    # todo!!! formatting structured abstracts
    # todo!! strip out inline formatting
    # todo!! replace maths with a placeholder string
    abstract = abstract_json.get("content")[0].get("text")
    return abstract


def author(authors_json):

    author_list = []
    for author in authors_json:
        author_json = OrderedDict()
        # todo!!! test and format group author name

        # affiliations
        affiliations = []
        for aff_json in author.get("affiliations"):
            affiliations.append(affiliation_string(aff_json))
        if affiliations:
            author_json["affiliation"] = "; ".join(affiliations)
        # name
        author_json["name"] = author.get("name").get("preferred")
        # orcid
        if author.get("orcid"):
            author_json["orcid_id"] = "https://orcid.org/%s" % author.get("orcid")

        author_list.append(author_json)
    return author_list


def affiliation_string(aff_json):
    "format one affiliation into a string value"
    aff_parts = []
    # name is a list, join it, although in reality it seems to only contain one item
    aff_parts.append(", ".join(aff_json.get("name")))
    if aff_json.get("address") and aff_json.get("address").get("formatted"):
        aff_parts = aff_parts + aff_json.get("address").get("formatted")
    return ", ".join(aff_parts)


def identifier(article_json):
    identifier_list = []
    # doi
    doi = OrderedDict()
    doi["id"] = article_json.get("doi")
    doi["type"] = "doi"
    identifier_list.append(doi)
    # eissn
    eissn = OrderedDict()
    eissn["id"] = EISSN
    eissn["type"] = "eissn"
    identifier_list.append(eissn)
    # elocationid
    elocationid = OrderedDict()
    elocationid["id"] = article_json.get("elocationId")
    elocationid["type"] = "elocationid"
    identifier_list.append(elocationid)
    return identifier_list


def journal(article_json):
    journal_json = OrderedDict()
    journal_json["volume"] = str(article_json.get("volume"))
    return journal_json


def keywords(keywords_json):
    keyword_list = keywords_json
    return keyword_list


def link(article_json):
    link_json = OrderedDict()
    link_json["content_type"] = "text/html"
    link_json["type"] = "fulltext"
    link_json["url"] = LINK_URL_PATTERN % article_json.get("id")
    return link_json


def month(date_struct):
    return str(date_struct.tm_mon)


def title(article_json):
    # todo!!! remove inline formatting tags
    title = article_json.get("title")
    return title


def year(date_struct):
    return str(date_struct.tm_year)
