import json
import os
from xml.etree.ElementTree import Element
from elifetools import xmlio
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, meca, preprint, utils
from activity.objects import MecaBaseActivity


class activity_ReplacePreprintPDF(MecaBaseActivity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ReplacePreprintPDF, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ReplacePreprintPDF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download preprint PDF and replace existing MECA PDF in the"
            " S3 bucket expanded folder"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {
            "pdf_url": None,
            "pdf_href": None,
            "download_pdf": None,
            "replace_pdf": None,
            "modify_manifest_xml": None,
            "upload_manifest_xml": None,
            "modify_article_xml": None,
            "upload_article_xml": None,
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_xml_path = session.get_value("article_xml_path")
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        pdf_url = session.get_value("pdf_url")
        expanded_folder = session.get_value("expanded_folder")

        if not pdf_url:
            self.logger.error(
                "%s, no pdf_url found in the session for %s, failing the workflow"
                % (self.name, version_doi)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.statuses["pdf_url"] = True

        self.make_activity_directories()

        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # download manifest.xml file
        self.logger.info(
            "%s, downloading manifest.xml for %s from %s"
            % (self.name, version_doi, resource_prefix)
        )

        (
            manifest_xml_file_path,
            manifest_storage_resource_origin,
        ) = self.download_manifest(storage, resource_prefix)

        old_pdf_href = pdf_href_from_manifest(manifest_xml_file_path)
        self.logger.info(
            "%s, got pdf_href %s from manifest.xml for %s"
            % (self.name, old_pdf_href, version_doi)
        )
        self.statuses["pdf_href"] = True

        # generate path to the PDF file
        content_subfolder = meca.meca_content_folder(article_xml_path)
        new_pdf_href = generate_new_pdf_href(article_id, version, content_subfolder)
        self.logger.info(
            "%s, generated new PDF href value %s for %s"
            % (self.name, new_pdf_href, version_doi)
        )
        to_file = os.path.join(self.directories.get("INPUT_DIR"), new_pdf_href)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(to_file), exist_ok=True)
        # download the PDF at pdf_url
        self.logger.info(
            "%s, downloading %s to %s for %s"
            % (self.name, pdf_url, to_file, version_doi)
        )
        utils.download_file(
            pdf_url, to_file, user_agent=getattr(self.settings, "user_agent", None)
        )
        self.statuses["download_pdf"] = True

        # replace PDF file in the S3 expanded folder
        self.logger.info(
            "%s, copying new pdf %s to the bucket expanded folder"
            % (self.name, new_pdf_href)
        )
        new_s3_resource = resource_prefix + "/" + new_pdf_href
        storage.set_resource_from_filename(new_s3_resource, to_file)
        # remove old PDF file
        if old_pdf_href:
            self.logger.info(
                "%s, removing old pdf %s from the bucket expanded folder"
                % (self.name, old_pdf_href)
            )
            old_s3_resource = resource_prefix + "/" + old_pdf_href
            storage.delete_resource(old_s3_resource)
            self.statuses["replace_pdf"] = True

        # format file detail transformations
        file_detail_list = [
            {
                "file_type": "article",
                "from_href": old_pdf_href,
                "href": new_pdf_href,
                "id": None,
                "title": None,
            }
        ]

        # modify manifest.xml file
        if old_pdf_href:
            # rewrite item tags in manifest file
            meca.rewrite_item_tags(
                manifest_xml_file_path,
                file_detail_list,
                version_doi,
                self.name,
                self.logger,
            )
        else:
            # add manifest.xml tags for PDF file
            meca.add_instance_tags(
                manifest_xml_file_path,
                file_detail_list,
                version_doi,
                self.name,
                self.logger,
            )

        # make manifest XML more pretty with added new line characters
        cleaner.pretty_manifest_xml(manifest_xml_file_path, version_doi)

        self.statuses["modify_manifest_xml"] = True

        # upload manifest to the bucket
        self.logger.info(
            "%s, updating manifest XML to %s"
            % (self.name, manifest_storage_resource_origin)
        )
        storage.set_resource_from_filename(
            manifest_storage_resource_origin, manifest_xml_file_path
        )

        self.statuses["upload_manifest_xml"] = True

        # download XML from the bucket folder

        # local path to the article XML file
        xml_file_path = os.path.join(self.directories.get("TEMP_DIR"), article_xml_path)

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        xml_storage_resource_origin = resource_prefix + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, xml_storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(xml_storage_resource_origin, open_file)

        # add / update self-uri tag in the article XML
        set_pdf_self_uri(xml_file_path, new_pdf_href.rsplit("/", 1)[-1], version_doi)
        self.statuses["modify_article_xml"] = True

        # upload the XML to the bucket
        self.logger.info(
            "%s, updating modified XML to %s" % (self.name, xml_storage_resource_origin)
        )
        storage.set_resource_from_filename(xml_storage_resource_origin, xml_file_path)

        self.statuses["upload_article_xml"] = True

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        return self.ACTIVITY_SUCCESS


def pdf_href_from_manifest(manifest_xml_file_path):
    "find the article PDF xlink:href from manifest.xml file"
    pdf_href = None
    # parse XML file
    root = cleaner.parse_manifest(manifest_xml_file_path)[0]
    # find PDF href from the instance tag in article item tag
    item_tag = root.find('.//{http://manuscriptexchange.org}item[@type="article"]')
    if item_tag is not None:
        instance_tag = item_tag.find(
            './/{http://manuscriptexchange.org}instance[@media-type="application/pdf"]'
        )
        if instance_tag is not None:
            pdf_href = instance_tag.get("href")

    return pdf_href


def generate_new_pdf_href(article_id, version, content_subfolder):
    "generate a new name for a preprint PDF"
    new_pdf_file_name = preprint.PREPRINT_PDF_FILE_NAME_PATTERN.format(
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


def set_pdf_self_uri(xml_file_path, pdf_file_name, identifier):
    "set or add a self-uri tag to article XML for an article PDF file"
    # Register namespaces
    xmlio.register_xmlns()

    # get the XML doctype
    xml_root, doctype_dict, processing_instructions = xmlio.parse(
        xml_file_path,
        return_doctype_dict=True,
        return_processing_instructions=True,
    )

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
    article_meta_tag.insert(insert_index, self_uri_tag)

    # write the XML root to disk
    cleaner.write_xml_file(
        xml_root, xml_file_path, identifier, doctype_dict, processing_instructions
    )
