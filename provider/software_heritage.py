"functions for processing deposits to Software Heritage"

import os
import requests
from collections import OrderedDict
from string import Template
from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement


FILE_NAME_FORMAT = "elife-%s-v%s-era.zip"
BUCKET_FOLDER = "software_heritage/run"


class MetaData(object):
    def __init__(self, file_name=None, article=None):
        self.id = None
        self.title = None
        self.codemeta = OrderedDict()
        self.codemeta["description"] = None

        self.swhdeposit = OrderedDict()
        self.swhdeposit["deposit"] = OrderedDict()
        self.swhdeposit["deposit"]["create_origin"] = OrderedDict()
        self.swhdeposit["deposit"]["create_origin"]["url"] = None

        if article:
            self.title = article.title
            if article.doi or article.title:
                self.codemeta["referencePublication"] = OrderedDict()
                self.codemeta["referencePublication"]["name"] = article.title
                self.codemeta["referencePublication"]["identifier"] = article.doi
            if article.license and article.license.href:
                self.codemeta["license"] = OrderedDict()
                self.codemeta["license"]["url"] = article.license.href
            self.codemeta["authors"] = []
            for author in [author for author in article.contributors]:
                author_dict = OrderedDict()
                if author.collab:
                    author_dict["name"] = author.collab
                else:
                    if not author.group_author_key:
                        author_dict["name"] = " ".join(
                            [
                                part
                                for part in [author.given_name, author.surname, author.suffix]
                                if part is not None
                            ]
                        )
                if not author_dict.get("name"):
                    continue

                if author.affiliations:
                    author_dict["affiliations"] = []
                    for aff in author.affiliations:
                        author_dict["affiliations"].append(aff.text)
                self.codemeta["authors"].append(author_dict)

        if file_name:
            self.id = file_name


def metadata(file_name, article):
    "generate metadata object for a deposit"
    metadata = MetaData(file_name, article)
    return metadata


def metadata_xml(element, pretty=False, indent=""):
    "generate string XML output from an Element object"
    encoding = "utf-8"
    rough_string = ElementTree.tostring(element, encoding)
    reparsed = minidom.parseString(rough_string)

    if pretty is True:
        return reparsed.toprettyxml(indent, encoding=encoding)
    return reparsed.toxml(encoding=encoding)


def metadata_element(metadata):
    "generate metadata XML Element from metadata object"
    root = Element("entry")
    root.set("xmlns", "http://www.w3.org/2005/Atom")
    root.set("xmlns:codemeta", "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0")
    root.set("xmlns:swhdeposit", "https://www.softwareheritage.org/schema/2018/deposit")
    # simple tags
    for tag_name in ["title", "id"]:
        if getattr(metadata, tag_name):
            tag = SubElement(root, tag_name)
            tag.text = getattr(metadata, tag_name)
    # swhdeposit tags
    swhdeposit(root, metadata)
    # codemeta tags
    codemeta(root, metadata)
    return root


def swhdeposit(root, metadata):
    "set swhdeposit:deposit XML tag"
    prefix = "swhdeposit"
    section_name = "deposit"
    tag_name = "create_origin"
    key = "url"
    url = metadata.swhdeposit.get("deposit").get("create_origin").get("url")
    if url:
        deposit_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        create_origin_tag = SubElement(deposit_tag, "%s:%s" % (prefix, tag_name))
        origin_tag = SubElement(
            create_origin_tag,
            "%s:origin" % prefix,
        )
        origin_tag.set(key, url)


def codemeta(root, metadata):
    "set codemeta prefixed XML tags"
    codemeta_simple(root, metadata)
    codemeta_reference_publication(root, metadata)
    codemeta_license(root, metadata)
    codemeta_authors(root, metadata)


def codemeta_simple(root, metadata):
    "set codemeta XML tags which have no child tags"
    prefix = "codemeta"
    for tag_name in ["description"]:
        if metadata.codemeta.get(tag_name):
            tag = SubElement(root, "%s:%s" % (prefix, tag_name))
            tag.text = metadata.codemeta.get(tag_name)


def codemeta_reference_publication(root, metadata):
    "set codemeta:referencePublication XML tags"
    prefix = "codemeta"
    section_name = "referencePublication"
    if metadata.codemeta.get(section_name):
        parent_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        for tag_name in ["name", "identifier"]:
            if metadata.codemeta.get(section_name).get(tag_name):
                tag = SubElement(parent_tag, "%s:%s" % (prefix, tag_name))
                tag.text = metadata.codemeta.get(section_name).get(tag_name)


def codemeta_license(root, metadata):
    "set codemeta:license XML tags"
    prefix = "codemeta"
    section_name = "license"
    tag_name = "url"
    if metadata.codemeta.get(section_name) and metadata.codemeta.get(section_name).get(
        tag_name
    ):
        parent_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        tag = SubElement(parent_tag, "%s:%s" % (prefix, tag_name))
        tag.text = metadata.codemeta.get(section_name).get(tag_name)


def codemeta_authors(root, metadata):
    "set codemeta:author XML tags"
    prefix = "codemeta"
    section_name = "author"
    if metadata.codemeta.get("authors"):
        for author in metadata.codemeta.get("authors"):
            author_tag = SubElement(root, "%s:%s" % (prefix, section_name))
            name_tag = SubElement(author_tag, "%s:name" % prefix)
            name_tag.text = author.get("name")
            codemeta_author_affiliations(author_tag, author)


def codemeta_author_affiliations(root, author):
    "set codemeta:affiliation XML tags"
    prefix = "codemeta"
    section_name = "affiliation"
    if author.get("affiliations"):
        for affiliation in author.get("affiliations"):
            affiliation_tag = SubElement(root, "%s:%s" % (prefix, section_name))
            affiliation_tag.text = affiliation


def readme(kwargs):
    "generate readme file using a template with string substitutions"
    string_template = None
    with open("template/swh_readme_template.txt", "r") as open_file:
        string_template = Template(open_file.read())
    if string_template:
        return string_template.safe_substitute(kwargs)
    return ""


def swh_post_request(
    url,
    auth_user,
    auth_pass,
    zip_file_path,
    atom_file_path,
    verify_ssl=False,
    logger=None,
):
    "POST data to SWH API endpoint"

    headers = {"In-Progress": "false"}

    zip_file_name = zip_file_path.split(os.sep)[-1]
    atom_file_name = atom_file_path.split(os.sep)[-1]

    multiple_files = [
        ("file", (zip_file_name, open(zip_file_path, "rb"), "application/zip")),
        ("atom", (atom_file_name, open(atom_file_path, "rb"), "application/atom+xml")),
    ]

    response = requests.post(
        url,
        files=multiple_files,
        verify=verify_ssl,
        headers=headers,
        auth=(auth_user, auth_pass),
    )

    if logger:
        logger.info(
            "Post zip file %s and atom file %s to SWH API: POST %s"
            % (zip_file_name, atom_file_name, url)
        )
        logger.info(
            "Response from SWH API: %s\n%s" % (response.status_code, response.content)
        )

    status_code = response.status_code
    if not 201 >= status_code >= 200:
        raise Exception(
            "Error posting zip file %s and atom file %s to SWH API: %s\n%s"
            % (zip_file_name, atom_file_name, status_code, response.content)
        )

    return response
