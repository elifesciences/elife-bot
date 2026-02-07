"functions for generating preprint XML"
import os
import re
from xml.etree.ElementTree import Element
import requests
from elifetools import xmlio, utils as etoolsutils
from elifearticle.article import (
    Article,
    ArticleDate,
)
from jatsgenerator import generate
from jatsgenerator.conf import raw_config, parse_raw_config
from provider import cleaner, download_helper, utils
from provider.storage_provider import storage_context


CONFIG_SECTION = "elife_preprint"

# path in the bucket for preprint XML
PREPRINT_AUTOMATION_XML_PATH_PATTERN = "automation/{article_id}/v{version}"

# file name of the preprint XML in the bucket
PREPRINT_AUTOMATION_XML_FILE_NAME_PATTERN = "article-source.xml"


# file name for new preprint PDF file
PREPRINT_PDF_FILE_NAME_PATTERN = "elife-preprint-{article_id}-v{version}.pdf"


# file name for new preprint XML file
PREPRINT_XML_FILE_NAME_PATTERN = "elife-preprint-{article_id}-v{version}.xml"


# DOI prefix to confirm version DOI value
DOI_PREFIX = "10.7554"


REQUESTS_TIMEOUT = (10, 60)


class PreprintArticleException(Exception):
    pass


def jatsgenerator_config(config_section, config_file):
    "parse the config values from the jatsgenerator config"
    return parse_raw_config(raw_config(config_section, config_file))


def build_simple_article(
    article_id, doi, title, version_doi=None, accepted_date_struct=None
):
    "instantiate a simple Article object for using in Crossref pending publication DOI deposit"
    try:
        article = Article(doi)
        article.version_doi = version_doi
        article.manuscript = article_id
        article.title = title
        if accepted_date_struct:
            article.add_date(ArticleDate("accepted", accepted_date_struct))
    except Exception as exception:
        raise PreprintArticleException(
            "Could not instantiate an Article object for article_id %s: %s"
            % (article_id, str(exception))
        )
    return article


def xml_filename(article_id, settings, version=None):
    "preprint XML filename from the configuration file"
    jats_config = jatsgenerator_config(
        CONFIG_SECTION, settings.jatsgenerator_config_file
    )
    filename = jats_config.get("xml_filename_pattern").format(manuscript=article_id)
    if version:
        filename = filename.replace(".xml", "-v%s.xml" % version)
    return filename


def preprint_xml(article, settings, pretty=True, indent=""):
    "generate preprint XML string from inputs"
    add_comment = True
    jats_config = jatsgenerator_config(
        CONFIG_SECTION, settings.jatsgenerator_config_file
    )
    article_xml = generate.ArticleXML(article, jats_config, add_comment)
    xml_string = article_xml.output_xml(pretty=pretty, indent=indent)
    return xml_string


def download_original_preprint_xml(settings, to_dir, article_id, version):
    "download the preprint server version of the XML"
    # get preprint server XML from a bucket
    real_filename = PREPRINT_AUTOMATION_XML_FILE_NAME_PATTERN
    bucket_name = settings.epp_data_bucket
    bucket_folder = PREPRINT_AUTOMATION_XML_PATH_PATTERN.format(
        article_id=article_id, version=version
    )

    article_xml_path = download_helper.download_file_from_s3(
        settings,
        real_filename,
        bucket_name,
        bucket_folder,
        to_dir,
    )

    return article_xml_path


def is_article_preprint(article_object):
    "check properties of an Article for whether it is considered to be a preprint"
    if (
        hasattr(article_object, "publication_state")
        and article_object.article_type == "preprint"
    ) or (
        hasattr(article_object, "publication_state")
        and article_object.publication_state == "reviewed preprint"
    ):
        return True
    return False


def expanded_folder_bucket_resource(settings, bucket_name, expanded_folder_name):
    "path to the expanded folder in the bucket"
    bucket_folder_name = expanded_folder_name.replace(os.sep, "/")
    return settings.storage_provider + "://" + bucket_name + "/" + bucket_folder_name


def find_xml_filename_in_expanded_folder(settings, bucket_resource):
    "find the preprint XML file name in the bucket expanded folder"
    storage = storage_context(settings)
    s3_key_names = storage.list_resources(bucket_resource)
    # for now the only XML file is the one to download
    for s3_key_name in s3_key_names:
        if s3_key_name.endswith(".xml"):
            return s3_key_name.split("/")[-1]
    return None


def download_from_expanded_folder(
    settings, directories, bucket_filename, bucket_resource, caller_name, logger
):
    "download the object from the bucket expanded folder"
    storage = storage_context(settings)
    file_path = os.path.join(directories.get("INPUT_DIR"), bucket_filename)
    with open(file_path, "wb") as open_file:
        storage_resource_origin = bucket_resource + "/" + bucket_filename
        logger.info(
            "%s, downloading %s to %s"
            % (caller_name, storage_resource_origin, file_path)
        )
        storage.get_resource_to_file(storage_resource_origin, open_file)
    return file_path


def get_preprint_pdf_url(endpoint_url, caller_name, user_agent=None):
    "from the API endpoint, get the preprint PDF URL if it exists"
    pdf_url = None

    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}

    response = requests.get(endpoint_url, timeout=REQUESTS_TIMEOUT, headers=headers)
    if response.status_code == 200:
        data = response.json()
        pdf_url = data.get("pdf")
    elif response.status_code != 404:
        raise RuntimeError(
            "%s, got a %s status code for %s"
            % (caller_name, response.status_code, endpoint_url)
        )
    return pdf_url


def generate_new_pdf_href(article_id, version, content_subfolder):
    "generate a new name for a preprint PDF"
    new_pdf_file_name = PREPRINT_PDF_FILE_NAME_PATTERN.format(
        article_id=utils.pad_msid(article_id), version=version
    )
    new_pdf_href = "/".join(
        [part for part in [content_subfolder, new_pdf_file_name] if part]
    )
    return new_pdf_href


def clear_pdf_self_uri(xml_root):
    "remove self-uri tag if its content-type is pdf"
    article_meta_tag = xml_root.find(".//front/article-meta")
    for self_uri_tag in article_meta_tag.findall('self-uri[@content-type="pdf"]'):
        article_meta_tag.remove(self_uri_tag)


def set_pdf_self_uri_tag(xml_root, pdf_file_name, identifier):
    "modify self-uri XML tag"
    # remove old self-uri tags
    clear_pdf_self_uri(xml_root)

    # determine where to insert self-uri tag
    insert_index = 0
    article_meta_tag = xml_root.find(".//front/article-meta")
    for index, tag in enumerate(article_meta_tag.findall("*")):
        if tag.tag in ["permissions"]:
            insert_index = index + 1
            break

    # add pdf self-uri tag
    self_uri_tag = Element("self-uri")
    self_uri_tag.set("content-type", "pdf")
    self_uri_tag.set("{http://www.w3.org/1999/xlink}href", pdf_file_name)
    self_uri_tag.tail = "\n"
    article_meta_tag.insert(insert_index, self_uri_tag)


def set_pdf_self_uri(xml_file_path, pdf_file_name, identifier):
    "set or add a self-uri tag to article XML for an article PDF file"
    # Register namespaces
    xmlio.register_xmlns()

    # get the XML doctype
    xml_root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file_path,
        return_doctype_dict=True,
        return_processing_instructions=True,
        insert_pis=True,
        insert_comments=True,
    )

    set_pdf_self_uri_tag(xml_root, pdf_file_name, identifier)

    # write the XML root to disk
    cleaner.write_xml_file(
        xml_root, xml_file_path, identifier, doctype_dict, processing_instructions
    )


def repair_entities(xml_file_path, caller_name, logger):
    "replace entities with unicode characters in XML file"
    # read file
    repaired_xml_string = None
    with open(xml_file_path, "rb") as open_file:
        xml_string = open_file.read()
    # replace entities
    try:
        repaired_xml_string = etoolsutils.named_entity_to_unicode(xml_string)
    except TypeError:
        # convert to string then back to bytes
        repaired_xml_string = bytes(
            etoolsutils.named_entity_to_unicode(utils.bytes_decode(xml_string)),
            encoding="utf-8",
        )
    except Exception as exception:
        logger.exception(
            "%s, unhandled exception repairing entities in %s: %s"
            % (caller_name, xml_file_path, str(exception))
        )
    # write to file
    if repaired_xml_string:
        with open(xml_file_path, "wb") as open_file:
            open_file.write(repaired_xml_string)


XML_NAMESPACES = {
    "ali": "http://www.niso.org/schemas/ali/1.0/",
    "mml": "http://www.w3.org/1998/Math/MathML",
    "xlink": "http://www.w3.org/1999/xlink",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def format_namespace_uri(attribute):
    "from a tag attribute value return the namespace URI"
    if attribute and "{" in attribute:
        return re.match(r"{.*?}", attribute)[0].replace("{", "").replace("}", "")
    return None


def attribute_namespace_uris(attributes):
    "from a set of attribute values return namespace URIs found in them"
    namespace_attributes = {attrib for attrib in attributes if attrib.startswith("{")}
    return {format_namespace_uri(attrib) for attrib in namespace_attributes if attrib}


def find_used_namespace_uris(xml_root):
    "from the Element find the namespace URIs used in tag attributes and tag names"
    all_attributes = set()
    # collect all unique tag attributes
    for tag in xml_root.iter("*"):
        # add tag name to the set too
        all_attributes.add(str(tag.tag))
        all_attributes = all_attributes.union(set(tag.attrib.keys()))
    return attribute_namespace_uris(all_attributes)


def modify_xml_namespaces(xml_file):
    "add XML namespaces even if not already found in the XML"

    # register namespaces
    xmlio.register_xmlns()

    # parse XML file
    root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file,
        return_doctype_dict=True,
        return_processing_instructions=True,
        insert_pis=True,
        insert_comments=True,
    )

    # find namespace URIs used in tag attributes
    used_namespace_uris = find_used_namespace_uris(root)

    # set a default doctype if not supplied
    if not doctype_dict:
        doctype_dict = {"name": "article", "pubid": None, "system": None}

    # add XML namespaces
    for prefix in XML_NAMESPACES:
        ns_attrib = "xmlns:%s" % prefix
        if XML_NAMESPACES.get(prefix) not in used_namespace_uris:
            root.set(ns_attrib, XML_NAMESPACES.get(prefix))

    # output the XML to file
    reparsed_string = xmlio.output(
        root,
        output_type=None,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )

    with open(xml_file, "wb") as open_file:
        open_file.write(reparsed_string)
