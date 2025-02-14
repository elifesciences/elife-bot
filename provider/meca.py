import os
from xml.etree import ElementTree
import requests
from provider import cleaner

REQUESTS_TIMEOUT = (10, 60)

# MECA file name configuration
MECA_FILE_NAME_PATTERN = "{article_id}-v{version}-meca.zip"

# path in the bucket to a MECA file
MECA_BUCKET_FOLDER = "/reviewed-preprints/"

# path to the manifest file in the zip or expanded folder
MANIFEST_XML_PATH = "manifest.xml"


def meca_file_name(article_id, version):
    "name for a MECA zip file"
    return MECA_FILE_NAME_PATTERN.format(article_id=article_id, version=version)


def meca_content_folder(article_xml_path):
    "from the MECA article XML file path get the folder name"
    try:
        return article_xml_path.rsplit("/", 1)[0]
    except AttributeError:
        return None


def get_meca_article_xml_path(folder_name, version_doi, caller_name, logger):
    "find manifest.xml and get the article XML tag href"
    # locate the bucket path to the manuscript XML file by reading the manifest.xml
    manifest_file_path = os.path.join(folder_name, MANIFEST_XML_PATH)
    try:
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
    except FileNotFoundError:
        if logger:
            logger.exception(
                "%s, manifest_file_path %s not found for version DOI %s"
                % (caller_name, manifest_file_path, version_doi)
            )
        return None
    xml_root = ElementTree.fromstring(xml_string)
    article_xml_path = None
    instance_tag = xml_root.find(
        './/{http://manuscriptexchange.org}instance[@media-type="application/xml"]'
    )
    if instance_tag is not None:
        article_xml_path = instance_tag.attrib.get("href")
    return article_xml_path


def post_xml_file(file_path, endpoint_url, user_agent, caller_name, logger):
    "POST the file_path to the XSLT endpoint"
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    file_name = file_path.split(os.sep)[-1]
    files = []
    logger.info(
        "%s, request to endpoint: POST file %s to %s",
        (caller_name, file_path, endpoint_url),
    )
    response = None
    with open(file_path, "rb") as open_file:
        files.append(("file", (file_name, open_file, "text/xml")))
        response = requests.post(
            endpoint_url, timeout=REQUESTS_TIMEOUT, headers=headers, files=files
        )
    if response and response.status_code not in [200]:
        raise Exception(
            "%s, error posting file %s to endpoint %s: %s, %s"
            % (
                caller_name,
                file_path,
                endpoint_url,
                response.status_code,
                response.content,
            )
        )
    if response and response.status_code == 200:
        return response.content
    return None


def post_to_endpoint(xml_file_path, endpoint_url, user_agent, caller_name, logger):
    "post XML file to endpoint, catch exceptions, return response content"
    try:
        response_content = post_xml_file(
            xml_file_path,
            endpoint_url,
            user_agent,
            caller_name,
            logger,
        )
    except Exception as exception:
        logger.exception(
            "%s, posting %s to endpoint %s: %s"
            % (
                caller_name,
                xml_file_path,
                endpoint_url,
                str(exception),
            )
        )
        response_content = None
    return response_content


def log_to_session(log_message, session):
    "save the message to the session"
    # add the log_message to the session variable
    log_messages = session.get_value("log_messages")
    if log_messages is None:
        log_messages = log_message
    else:
        log_messages += log_message
    session.store_value("log_messages", log_messages)


def collect_transformation_file_details(
    variant_data, root, file_transformations, content_subfolder
):
    "file details for use in XML from the file transformation data"
    file_detail_list = []
    # get metadata from XML
    fig_href_map = {}

    for fig_tag in root.findall(
        ".//sub-article//%s" % variant_data.get("parent_tag_name")
    ):
        fig_id = fig_tag.get("id")
        label_tag = fig_tag.find("./label")
        label = None
        if label_tag is not None:
            label = label_tag.text
        graphic_tag = fig_tag.find(variant_data.get("graphic_tag_name"))
        if graphic_tag is not None:
            href = graphic_tag.get("{http://www.w3.org/1999/xlink}href")
            if href:
                fig_href_map[href] = {}
                fig_href_map[href]["href"] = href
                fig_href_map[href]["id"] = fig_id
                fig_href_map[href]["label"] = label

    for file_transformation in file_transformations:
        if file_transformation[1].xml_name in fig_href_map:
            fig_detail = fig_href_map[file_transformation[1].xml_name]
            file_detail = {}
            file_detail["file_type"] = variant_data.get("file_type")
            # add content subfolder if provided
            file_detail["from_href"] = "/".join(
                [
                    path_part
                    for path_part in [
                        content_subfolder,
                        file_transformation[0].xml_name,
                    ]
                    if path_part
                ]
            )
            file_detail["href"] = "/".join(
                [
                    path_part
                    for path_part in [content_subfolder, fig_detail.get("href")]
                    if path_part
                ]
            )
            file_detail["id"] = fig_detail.get("id")
            file_detail["title"] = fig_detail.get("label")
            file_detail_list.append(file_detail)

    return file_detail_list


def rewrite_item_tags(
    manifest_xml_path, file_detail_list, version_doi, caller_name, logger
):
    "rewrite existing item tags in a manifest XML file"
    # parse XML file
    root, doctype_dict, processing_instructions = cleaner.parse_manifest(
        manifest_xml_path
    )
    href_file_detail_map = {
        file_detail.get("from_href"): file_detail
        for file_detail in file_detail_list
        if file_detail.get("from_href")
    }
    logger.info(
        "%s, starting to rewrite %s item tags in the manifest for version DOI %s"
        % (caller_name, len(href_file_detail_map), version_doi)
    )

    for item_tag in root.findall(".//{http://manuscriptexchange.org}item"):
        instance_tag = item_tag.find(".//{http://manuscriptexchange.org}instance")
        # match the href of the tag
        if (
            instance_tag is not None
            and instance_tag.get("href") in href_file_detail_map
        ):
            logger.info(
                "%s, modifying item tag for href %s for version DOI %s"
                % (caller_name, instance_tag.get("href"), version_doi)
            )
            file_details = href_file_detail_map.get(instance_tag.get("href"))
            if file_details.get("href"):
                logger.info(
                    "%s, rewriting item tag for href %s for version DOI %s"
                    % (caller_name, instance_tag.get("href"), version_doi)
                )
                # remove old XML data
                item_tag.remove(instance_tag)
                cleaner.remove_tag_attributes(item_tag)
                # rewrite the item tag data
                cleaner.populate_item_tag(item_tag, file_details)
            else:
                logger.info(
                    "%s, removing item tag for href %s for version DOI %s"
                    % (caller_name, instance_tag.get("href"), version_doi)
                )
                # remove the item tag
                root.remove(item_tag)

    # write XML file to disk
    cleaner.write_manifest_xml_file(
        root,
        manifest_xml_path,
        version_doi,
        doctype_dict=doctype_dict,
        processing_instructions=processing_instructions,
    )
