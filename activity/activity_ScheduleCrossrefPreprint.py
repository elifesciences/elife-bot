import json
import os
from provider import cleaner, outbox_provider, preprint
from provider.execution_context import get_session
from activity.objects import Activity


class activity_ScheduleCrossrefPreprint(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ScheduleCrossrefPreprint, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ScheduleCrossrefPreprint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue preprint article XML for depositing as a "
            "posted_content, and for depositing peer reviews, to Crossref"
        )
        self.logger = logger
        self.pretty_name = "Schedule Crossref Preprint"

        # For copying to S3 bucket outbox
        self.crossref_posted_content_outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder("DepositCrossrefPostedContent")
        )
        self.crossref_peer_review_outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder("DepositCrossrefPeerReview")
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        try:
            if data and "standalone" in data and data["standalone"]:
                article_id = data.get("article_id")
                version = data.get("version")
            else:
                # get data from the session
                run = data["run"]
                session = get_session(self.settings, data, run)
                article_id = session.get_value("article_id")
                version = session.get_value("version")
        except:
            self.logger.exception("Error starting Schedule Crossref Preprint activity")
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info("%s, article_id: %s" % (self.name, article_id))
        self.logger.info("%s, version: %s" % (self.name, version))

        # first check if required settings are available
        if not hasattr(self.settings, "epp_data_bucket"):
            self.logger.info(
                "No epp_data_bucket in settings, skipping %s for article_id %s, version %s"
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.epp_data_bucket:
            self.logger.info(
                "epp_data_bucket in settings is blank, skipping %s for article_id %s, version %s"
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_SUCCESS

        # get docmap data
        try:
            docmap_string = cleaner.get_docmap_string_with_retry(
                self.settings, article_id, self.name, self.logger
            )
        except Exception:
            self.logger.exception(
                (
                    "%s, exception raised to get docmap_string"
                    " using retries for article_id %s version %s"
                )
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # populate the article object
        try:
            article = preprint.build_preprint_article(
                self.settings,
                article_id,
                version,
                docmap_string,
                self.directories.get("TEMP_DIR"),
                self.logger,
            )
        except Exception:
            # handle if article could not be built
            self.logger.exception(
                "%s, exception raised when building the article object for article_id %s version %s"
                % (self.name, article_id, version)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # continue if article could be populated
        # generate preprint XML from data sources
        xml_file_name = preprint.xml_filename(article_id, self.settings, version)
        xml_file_path = os.path.join(self.directories.get("INPUT_DIR"), xml_file_name)
        xml_string = preprint.preprint_xml(article, self.settings)
        with open(xml_file_path, "wb") as open_file:
            open_file.write(xml_string)

        # upload to the posted_content outbox folder
        self.upload_file_to_outbox_folder(
            xml_file_path, self.crossref_posted_content_outbox_folder
        )

        # upload to the peer_review outbox folder
        self.upload_file_to_outbox_folder(
            xml_file_path, self.crossref_peer_review_outbox_folder
        )

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def upload_file_to_outbox_folder(self, file_path, outbox_folder_name):
        "add the file to the outbox folder in the S3 bucket"
        outbox_provider.upload_files_to_s3_folder(
            self.settings,
            self.settings.poa_packaging_bucket,
            outbox_folder_name,
            [file_path],
        )

        self.logger.info(
            ("%s, uploaded %s to S3 bucket %s, folder %s")
            % (
                self.name,
                file_path,
                self.settings.poa_packaging_bucket,
                outbox_folder_name,
            )
        )
