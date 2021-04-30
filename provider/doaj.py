import re
import time
from collections import OrderedDict
from elifetools import utils as etoolsutils


REMOVE_TITLE_TAGS = ["b", "i", "sub", "sup"]
REMOVE_ABSTRACT_TAGS = ["a", "b", "i", "span", "sub", "sup"]


def substitute_math_tags(string, replacement="[Formula: see text]"):
    "eplace math tags with a string, similar to function in elifepubmed library"
    if not string:
        return string
    # match over newlines with DOTALL for kitchen sink testing and if found in real articles
    for tag_match in re.finditer("<math(.*?)>(.*?)</math>", string, re.DOTALL):
        old_tag = "<math%s>%s</math>" % (tag_match.group(1), tag_match.group(2))
        string = string.replace(old_tag, replacement)
    return string


def doaj_json(article_json, settings=None):
    doaj_json = OrderedDict()
    doaj_json["bibjson"] = bibjson(article_json, settings)
    return doaj_json


def bibjson(article_json, settings=None):
    bibjson = OrderedDict()
    bibjson["abstract"] = abstract(article_json.get("abstract", {}))
    bibjson["author"] = author(article_json.get("authors", []))
    bibjson["identifier"] = identifier(
        article_json, eissn=getattr(settings, "journal_eissn", None)
    )
    bibjson["journal"] = journal(article_json)
    bibjson["keywords"] = keywords(article_json.get("keywords", []))
    bibjson["link"] = link(
        article_json, url_link_pattern=getattr(settings, "doaj_url_link_pattern", None)
    )
    published_date = time.strptime(article_json["published"], "%Y-%m-%dT%H:%M:%SZ")
    bibjson["month"] = month(published_date)
    bibjson["title"] = title(article_json)
    bibjson["year"] = year(published_date)
    return bibjson


def abstract(abstract_json):
    # collapse abstract content into a single string
    abstract_parts = []
    for content_block in abstract_json.get("content"):
        if content_block.get("type") == "section":
            # concatenate structured abstract content
            content = content_block.get("content")[0].get("text")
            abstract_parts.append("%s %s" % (content_block.get("title"), content))
        else:
            abstract_parts.append(content_block.get("text"))
    abstract = "\n".join(abstract_parts)
    # replace maths with a placeholder string
    abstract = substitute_math_tags(abstract, "[Formula: see text]")
    # remove inline formatting tags
    for tag_name in REMOVE_ABSTRACT_TAGS:
        abstract = etoolsutils.remove_tag(tag_name, abstract)
    return abstract


def author(authors_json):

    author_list = []
    for author in authors_json:
        author_json = OrderedDict()

        # affiliations
        affiliations = []
        for aff_json in author.get("affiliations", []):
            affiliations.append(affiliation_string(aff_json))
        if affiliations:
            author_json["affiliation"] = "; ".join(affiliations)

        # name
        if author.get("type") == "group":
            # format group author name
            author_json["name"] = author.get("name")
        else:
            # person name
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


def identifier(article_json, eissn=None):
    identifier_list = []
    # doi
    doi = OrderedDict()
    doi["id"] = article_json.get("doi")
    doi["type"] = "doi"
    identifier_list.append(doi)
    # eissn
    if eissn:
        eissn_json = OrderedDict()
        eissn_json["id"] = eissn
        eissn_json["type"] = "eissn"
        identifier_list.append(eissn_json)
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
    keyword_list = []
    for keyword in keywords_json:
        # check for any HTML tags to remove
        if "<" in keyword:
            for tag_name in REMOVE_TITLE_TAGS:
                keyword = etoolsutils.remove_tag(tag_name, keyword)
        keyword_list.append(keyword)
    return keyword_list


def link(article_json, url_link_pattern=None):
    link_list = []
    link_json = OrderedDict()
    if url_link_pattern:
        link_json["content_type"] = "text/html"
        link_json["type"] = "fulltext"
        link_json["url"] = url_link_pattern.format(article_id=article_json.get("id"))
        link_list.append(link_json)
    return link_list


def month(date_struct):
    return str(date_struct.tm_mon)


def title(article_json):
    title = article_json.get("title")
    # remove inline formatting tags
    for tag_name in REMOVE_TITLE_TAGS:
        title = etoolsutils.remove_tag(tag_name, title)
    return title


def year(date_struct):
    return str(date_struct.tm_year)
