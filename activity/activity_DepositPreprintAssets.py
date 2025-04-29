import os
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import meca, preprint, utils
from activity.objects import MecaBaseActivity


class activity_DepositPreprintAssets(MecaBaseActivity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DepositPreprintAssets, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DepositPreprintAssets"
        self.pretty_name = "Deposit preprint assets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit preprint assets to bucket"
        self.logger = logger

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_xml_path = session.get_value("article_xml_path")
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        expanded_folder = session.get_value("expanded_folder")

        storage = storage_context(self.settings)

        # download manifest.xml file
        expanded_resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        self.logger.info(
            "%s, downloading manifest.xml for %s from %s"
            % (self.name, version_doi, expanded_resource_prefix)
        )

        self.download_manifest(storage, expanded_resource_prefix)

        # get article PDF path from the manifest.xml
        article_pdf_path = meca.get_meca_article_pdf_path(
            self.directories.get("TEMP_DIR"), self.name, version_doi, self.logger
        )
        self.logger.info(
            "%s, got article_pdf_path %s for %s"
            % (self.name, article_pdf_path, version_doi)
        )

        # generate new XML file name
        xml_file = preprint.PREPRINT_XML_FILE_NAME_PATTERN.format(
            article_id=utils.pad_msid(article_id), version=version
        )
        # CDN PDF file name
        pdf_file = article_pdf_path.rsplit("/", 1)[-1]

        # copy resources from expanded folder to CDN bucket folder

        # dict of files to copy, from: to
        assets_dict = {article_pdf_path: pdf_file, article_xml_path: xml_file}
        self.logger.info("%s, assets to copy: %s" % (self.name, assets_dict))
        cdn_bucket_name = (
            self.settings.publishing_buckets_prefix + self.settings.preprint_cdn_bucket
        )
        dest_resource_prefix = (
            self.settings.storage_provider
            + "://"
            + cdn_bucket_name
            + "/"
            + utils.pad_msid(article_id)
        )
        try:
            for from_file, to_file in assets_dict.items():
                from_resource = expanded_resource_prefix + "/" + from_file
                to_resource = dest_resource_prefix + "/" + to_file
                self.logger.info(
                    "%s, copying %s to %s" % (self.name, from_resource, to_resource)
                )
                storage.copy_resource(from_resource, to_resource)
        except Exception as exception:
            self.logger.exception(
                "%s, exception when depositing assets: %s" % (self.name, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # Clean up disk
        self.clean_tmp_dir()

        return self.ACTIVITY_SUCCESS
