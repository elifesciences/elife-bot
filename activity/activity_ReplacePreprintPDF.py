import json
import os
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, utils
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
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        version_doi = session.get_value("version_doi")
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

        manifest_xml_file_path = self.download_manifest(storage, resource_prefix)[0]

        pdf_href = pdf_href_from_manifest(manifest_xml_file_path)
        self.logger.info(
            "%s, got pdf_href %s from manifest.xml for %s"
            % (self.name, pdf_href, version_doi)
        )
        self.statuses["pdf_href"] = True

        # generate path to the PDF file
        to_file = os.path.join(self.directories.get("INPUT_DIR"), pdf_href)
        # create folders if they do not exist
        os.makedirs(os.path.dirname(to_file), exist_ok=True)
        # download the PDF at pdf_url
        self.logger.info("%s, downloading %s to %s" % (self.name, pdf_url, to_file))
        utils.download_file(
            pdf_url, to_file, user_agent=getattr(self.settings, "user_agent", None)
        )
        self.statuses["download_pdf"] = True

        # replace PDF file in the S3 expanded folder
        self.logger.info(
            "%s, replacing pdf %s in the bucket expanded folder" % (self.name, pdf_href)
        )
        s3_resource = resource_prefix + "/" + pdf_href
        storage.set_resource_from_filename(s3_resource, to_file)
        self.statuses["replace_pdf"] = True

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
