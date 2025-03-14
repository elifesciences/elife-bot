"functions for processing deposits to Software Heritage"

import os
import re
from collections import OrderedDict
from string import Template
from xml.etree.ElementTree import Element, SubElement
import requests


FILE_NAME_FORMAT = "elife-%s-v%s-era.zip"
BUCKET_FOLDER = "software_heritage/run"


class MetaData:
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
            for author in article.contributors:
                author_dict = OrderedDict()
                if author.collab:
                    author_dict["name"] = author.collab
                elif not author.group_author_key:
                    author_dict["name"] = " ".join(
                        [
                            part
                            for part in [
                                author.given_name,
                                author.surname,
                                author.suffix,
                            ]
                            if part is not None
                        ]
                    )
                if not author_dict.get("name"):
                    continue

                if author.affiliations:
                    author_dict["affiliations"] = [
                        aff.text for aff in author.affiliations
                    ]

                self.codemeta["authors"].append(author_dict)

        if file_name:
            self.id = file_name


def metadata(file_name, article):
    "generate metadata object for a deposit"
    metadata_object = MetaData(file_name, article)
    return metadata_object


def metadata_element(metadata_object):
    "generate metadata XML Element from metadata object"
    root = Element("entry")
    root.set("xmlns", "http://www.w3.org/2005/Atom")
    root.set("xmlns:codemeta", "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0")
    root.set("xmlns:swhdeposit", "https://www.softwareheritage.org/schema/2018/deposit")
    # simple tags
    for tag_name in ["title", "id"]:
        if getattr(metadata_object, tag_name):
            tag = SubElement(root, tag_name)
            tag.text = getattr(metadata_object, tag_name)
    # swhdeposit tags
    swhdeposit(root, metadata_object)
    # codemeta tags
    codemeta(root, metadata_object)
    return root


def swhdeposit(root, metadata_object):
    "set swhdeposit:deposit XML tag"
    prefix = "swhdeposit"
    section_name = "deposit"
    tag_name = "create_origin"
    key = "url"
    url = metadata_object.swhdeposit.get("deposit").get("create_origin").get("url")
    if url:
        deposit_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        create_origin_tag = SubElement(deposit_tag, "%s:%s" % (prefix, tag_name))
        origin_tag = SubElement(
            create_origin_tag,
            "%s:origin" % prefix,
        )
        origin_tag.set(key, url)


def codemeta(root, metadata_object):
    "set codemeta prefixed XML tags"
    codemeta_simple(root, metadata_object)
    codemeta_reference_publication(root, metadata_object)
    codemeta_license(root, metadata_object)
    codemeta_authors(root, metadata_object)


def codemeta_simple(root, metadata_object):
    "set codemeta XML tags which have no child tags"
    prefix = "codemeta"
    for tag_name in ["description"]:
        if metadata_object.codemeta.get(tag_name):
            tag = SubElement(root, "%s:%s" % (prefix, tag_name))
            tag.text = metadata_object.codemeta.get(tag_name)


def codemeta_reference_publication(root, metadata_object):
    "set codemeta:referencePublication XML tags"
    prefix = "codemeta"
    section_name = "referencePublication"
    if metadata_object.codemeta.get(section_name):
        parent_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        for tag_name in ["name", "identifier"]:
            if metadata_object.codemeta.get(section_name).get(tag_name):
                tag = SubElement(parent_tag, "%s:%s" % (prefix, tag_name))
                tag.text = metadata_object.codemeta.get(section_name).get(tag_name)


def codemeta_license(root, metadata_object):
    "set codemeta:license XML tags"
    prefix = "codemeta"
    section_name = "license"
    tag_name = "url"
    if metadata_object.codemeta.get(section_name) and metadata_object.codemeta.get(
        section_name
    ).get(tag_name):
        parent_tag = SubElement(root, "%s:%s" % (prefix, section_name))
        tag = SubElement(parent_tag, "%s:%s" % (prefix, tag_name))
        tag.text = metadata_object.codemeta.get(section_name).get(tag_name)


def codemeta_authors(root, metadata_object):
    "set codemeta:author XML tags"
    prefix = "codemeta"
    section_name = "author"
    if metadata_object.codemeta.get("authors"):
        for author in metadata_object.codemeta.get("authors"):
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


def display_to_origin(display):
    """
    from the display value, an stencila article version,
    trim it to be the SWH origin value

    e.g. for display value
    https://elife.stencila.io/article-30274/v99/
    return https://elife.stencila.io/article-30274/
    """
    if not display:
        return None
    match_pattern = re.compile(r"^(https://elife.stencila.io/.*?/).*$")
    return match_pattern.sub(r"\1", display)


def swh_post_request(
    url,
    auth_user,
    auth_pass,
    zip_file_path,
    atom_file_path,
    in_progress=False,
    verify_ssl=False,
    logger=None,
):
    "POST data to SWH API endpoint"

    headers = {"In-Progress": "%s" % str(in_progress).lower()}

    zip_file_name = zip_file_path.split(os.sep)[-1] if zip_file_path else None
    atom_file_name = atom_file_path.split(os.sep)[-1] if atom_file_path else None

    if zip_file_path and atom_file_path:
        # multiple files, send with a Content-Type: multipart/form-data header
        multiple_files = []
        multiple_files.append(
            ("file", (zip_file_name, open(zip_file_path, "rb"), "application/zip"))
        )
        multiple_files.append(
            (
                "atom",
                (atom_file_name, open(atom_file_path, "rb"), "application/atom+xml"),
            )
        )

        response = requests.post(
            url,
            files=multiple_files,
            verify=verify_ssl,
            headers=headers,
            auth=(auth_user, auth_pass),
        )
    elif zip_file_path:
        # if only a zip file, send with a Content-Type: application/zip header
        # also must include a Content-Disposition header
        with open(zip_file_path, "rb") as payload:
            headers["Content-Type"] = "application/zip"
            headers["Content-Disposition"] = 'attachment; filename="%s"' % zip_file_name
            response = requests.post(
                url,
                data=payload,
                verify=verify_ssl,
                headers=headers,
                auth=(auth_user, auth_pass),
            )

    if logger:
        file_details = []
        if zip_file_path:
            file_details.append("zip file %s" % zip_file_name)
        if atom_file_path:
            file_details.append("atom file %s" % atom_file_name)

        logger.info("Post %s to SWH API: POST %s" % (", ".join(file_details), url))
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


def swh_origin_exists(url_pattern, origin, verify_ssl=False, logger=None):
    "check Software Heritage API for whether an origin already exists"
    url = url_pattern.format(origin=origin)

    if logger:
        logger.info("Checking if SWH origin exists at API URL %s" % url)
    response = requests.head(
        url,
        verify=verify_ssl,
    )
    if logger:
        logger.info("SWH origin status code %s" % response.status_code)
    return_value = None
    if response.status_code == 404:
        return_value = False
    elif response.status_code == 200:
        return_value = True
    if logger:
        logger.info(
            "Returning SWH origin exists value of %s for origin %s"
            % (return_value, origin)
        )
    return return_value
