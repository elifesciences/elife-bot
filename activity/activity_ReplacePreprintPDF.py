import json
import os
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
            "pdf_s3_path": None,
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
        pdf_s3_path = session.get_value("pdf_s3_path")
        expanded_folder = session.get_value("expanded_folder")

        if not pdf_s3_path:
            self.logger.error(
                "%s, no pdf_s3_path found in the session for %s, failing the workflow"
                % (self.name, version_doi)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.statuses["pdf_s3_path"] = True

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
        new_pdf_href = preprint.generate_new_pdf_href(
            article_id, version, content_subfolder
        )
        self.logger.info(
            "%s, generated new PDF href value %s for %s"
            % (self.name, new_pdf_href, version_doi)
        )
        to_file = os.path.join(self.directories.get("INPUT_DIR"), new_pdf_href)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(to_file), exist_ok=True)
        # download the PDF at pdf_s3_path
        pdf_resource_origin = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + pdf_s3_path
        )
        self.logger.info(
            "%s, downloading %s to %s for %s"
            % (self.name, pdf_s3_path, to_file, version_doi)
        )
        with open(to_file, "wb") as open_file:
            storage.get_resource_to_file(pdf_resource_origin, open_file)
        self.statuses["download_pdf"] = True

        # replace PDF file in the S3 expanded folder
        self.logger.info(
            "%s, copying new pdf %s to the bucket expanded folder"
            % (self.name, new_pdf_href)
        )
        new_s3_resource = resource_prefix + "/" + new_pdf_href
        storage.set_resource_from_filename(new_s3_resource, to_file)
        # remove old PDF file
        if old_pdf_href == new_pdf_href:
            self.logger.info(
                "%s, old pdf %s the same name as new pdf %s for %s"
                % (self.name, old_pdf_href, new_pdf_href, version_doi)
            )
        elif old_pdf_href:
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
        preprint.set_pdf_self_uri(
            xml_file_path, new_pdf_href.rsplit("/", 1)[-1], version_doi
        )
        self.statuses["modify_article_xml"] = True

        # upload the XML to the bucket
        self.logger.info(
            "%s, updating modified XML to %s" % (self.name, xml_storage_resource_origin)
        )
        storage.set_resource_from_filename(xml_storage_resource_origin, xml_file_path)

        self.statuses["upload_article_xml"] = True

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

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
