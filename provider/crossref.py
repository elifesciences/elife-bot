import os
import time
from collections import OrderedDict
from xml.etree.ElementTree import SubElement
import requests
from elifearticle.article import ArticleDate
from elifecrossref import generate, related
from elifecrossref.conf import raw_config, parse_raw_config
from provider import lax_provider, utils


def override_tmp_dir(tmp_dir):
    """explicit override of TMP_DIR in the generate module"""
    if tmp_dir:
        generate.TMP_DIR = tmp_dir


def elifecrossref_config(settings):
    "parse the config values from the elifecrossref config"
    return parse_raw_config(
        raw_config(
            settings.elifecrossref_config_section, settings.elifecrossref_config_file
        )
    )


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


def contributor_orcid_authenticated(article, orcid_authenticated):
    "set the orcid_authenticated attribute of contributor objects in the article"
    for contributor in article.contributors:
        if hasattr(contributor, "orcid_authenticated"):
            contributor.orcid_authenticated = orcid_authenticated
    return article


def set_article_pub_date(article, crossref_config, settings, logger):
    """if there is no pub date then set it from lax data"""
    # Check for a pub date
    article_pub_date = article_first_pub_date(crossref_config, article)
    # if no date was found then look for one on Lax
    if not article_pub_date:
        lax_pub_date = lax_provider.article_publication_date(
            article.manuscript, settings, logger
        )
        if lax_pub_date:
            date_struct = time.strptime(lax_pub_date, utils.S3_DATE_FORMAT)
            pub_date_object = ArticleDate(
                crossref_config.get("pub_date_types")[0], date_struct
            )
            article.add_date(pub_date_object)


def set_article_version(article, settings):
    """if there is no version then set it from lax data"""
    if not article.version:
        lax_version = lax_provider.article_highest_version(article.manuscript, settings)
        if lax_version:
            article.version = lax_version


def article_first_pub_date(crossref_config, article):
    "find the first article pub date from the list of crossref config pub_date_types"
    pub_date = None
    if crossref_config.get("pub_date_types"):
        # check for any useable pub date
        for pub_date_type in crossref_config.get("pub_date_types"):
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


def crossref_data_payload(
    crossref_login_id, crossref_login_passwd, operation="doMDUpload"
):
    """assemble a requests data payload for Crossref endpoint"""
    return {
        "operation": operation,
        "login_id": crossref_login_id,
        "login_passwd": crossref_login_passwd,
    }


def upload_files_to_endpoint(url, payload, xml_files):
    """Using an HTTP POST, deposit the file to the Crossref endpoint"""

    # Default return status
    status = True
    http_detail_list = []

    for xml_file in xml_files:
        files = {"file": open(xml_file, "rb")}

        response = requests.post(url, data=payload, files=files)

        # Check for good HTTP status code
        if response.status_code != 200:
            status = False
        # print response.text
        http_detail_list.append("XML file: " + xml_file)
        http_detail_list.append("HTTP status: " + str(response.status_code))
        http_detail_list.append("HTTP response: " + response.text)

    return status, http_detail_list


def generate_crossref_xml_to_disk(
    article_object_map,
    crossref_config,
    good_xml_files,
    bad_xml_files,
    submission_type="journal",
    pretty=False,
    indent="",
):
    """from the article object generate crossref deposit XML"""
    for xml_file, article in list(article_object_map.items()):
        try:
            # Will write the XML to the TMP_DIR
            generate.crossref_xml_to_disk(
                [article],
                crossref_config,
                submission_type=submission_type,
                pretty=pretty,
                indent=indent,
            )
            # Add filename to the list of good files
            good_xml_files.append(xml_file)
        except:
            # Add the file to the list of bad files
            bad_xml_files.append(xml_file)
    # Any files generated is a sucess, even if one failed
    return True


def build_crossref_xml(
    article_object_map,
    crossref_config,
    good_xml_files,
    bad_xml_files,
    submission_type="journal",
):
    "from the article object build CrossrefXML objects"
    object_list = []
    for xml_file, article in list(article_object_map.items()):
        try:
            # Will write the XML to the TMP_DIR
            object_list.append(
                generate.build_crossref_xml(
                    [article],
                    crossref_config,
                    submission_type=submission_type,
                )
            )
            # Add filename to the list of good files
            good_xml_files.append(xml_file)
        except:
            # Add the file to the list of bad files
            bad_xml_files.append(xml_file)
    # Any files generated is a sucess, even if one failed
    return object_list


def set_version_doi_on_review_articles(article_object_map):
    "for peer review deposits set the related article of each review article to be the version_doi"
    for xml_file, article in list(article_object_map.items()):
        if article.version_doi:
            for review_article in article.review_articles:
                for related_article in review_article.related_articles:
                    related_article.doi = article.version_doi


def add_rel_program_tag(root):
    "add a rel:program tag to a Crossref deposit ElementTree root, if missing"
    if not find_rel_program_tag(root):
        namespaces = {"rel": "http://www.crossref.org/relations.xsd"}
        journal_article_tag = root.find("./body/journal/journal_article", namespaces)
        if not journal_article_tag:
            SubElement(journal_article_tag, "rel:program")


def find_rel_program_tag(root):
    "find the rel:program tag from Crossref deposit ElementTree root"
    namespaces = {"rel": "http://www.crossref.org/relations.xsd"}
    journal_article_tag = root.find("./body/journal/journal_article", namespaces)
    return journal_article_tag.find("rel:program")


def clear_rel_program_tag(c_xml):
    "remove child tags in the rel:program tag from CrossrefXML object XML root"
    rel_program_tag = find_rel_program_tag(c_xml.root)
    if rel_program_tag:
        child_tags = rel_program_tag.findall("*")
        for sub_tag in child_tags:
            rel_program_tag.remove(sub_tag)


def add_is_same_as_tag(rel_program_tag, doi):
    "add doi as intra_work_relation isSameAs tag to the rel:program tag"
    related_item_tag = SubElement(rel_program_tag, "rel:related_item")
    related.set_related_item_work_relation(
        related_item_tag,
        "intra_work_relation",
        "isSameAs",
        "doi",
        doi,
    )


def add_is_version_of_tag(rel_program_tag, doi):
    "add doi as intra_work_relation isVersionOf tag to the rel:program tag"
    related_item_tag = SubElement(rel_program_tag, "rel:related_item")
    related.set_related_item_work_relation(
        related_item_tag,
        "intra_work_relation",
        "isVersionOf",
        "doi",
        doi,
    )


def crossref_xml_to_disk(c_xml, output_dir, pretty=False, indent=""):
    "generate XML string from the CrossrefXML object and write it to the disk"
    xml_string = c_xml.output_xml(pretty=pretty, indent=indent)
    # Write to file
    filename = os.path.join(output_dir, "%s.xml" % c_xml.batch_id)
    with open(filename, "wb") as open_file:
        open_file.write(xml_string.encode("utf-8"))


def doi_exists(doi, logger):
    """given a DOI check if it exists in Crossref"""
    exists = False
    doi_url = utils.get_doi_url(doi)
    response = requests.head(doi_url)
    if 300 <= response.status_code < 400:
        exists = True
    elif response.status_code < 300 or response.status_code >= 500:
        logger.info("Status code for %s was %s" % (doi, response.status_code))
    return exists


def doi_does_not_exist(doi, logger):
    """given a DOI check if it does not exist at Crossref"""
    does_not_exist = None
    doi_url = utils.get_doi_url(doi)
    response = requests.head(doi_url)
    logger.info("Status code for %s was %s" % (doi, response.status_code))
    if 200 <= response.status_code < 400:
        does_not_exist = False
    elif response.status_code < 500:
        does_not_exist = True
    return does_not_exist
