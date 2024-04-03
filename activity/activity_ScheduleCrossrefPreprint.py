import json
import os
from provider import outbox_provider, preprint
from provider.execution_context import get_session
from provider.storage_provider import storage_context
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
                expanded_folder_name = session.get_value("expanded_folder")
                expanded_bucket_name = (
                    self.settings.publishing_buckets_prefix
                    + self.settings.expanded_bucket
                )
        except:
            self.logger.exception("Error starting %s activity" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info("%s, article_id: %s" % (self.name, article_id))
        self.logger.info("%s, version: %s" % (self.name, version))

        # generate preprint XML if standalone
        xml_file_path = None
        if data and "standalone" in data and data["standalone"]:
            # first check if required settings are available
            if not hasattr(self.settings, "epp_data_bucket"):
                self.logger.info(
                    "No epp_data_bucket in settings, skipping %s for article_id %s, version %s"
                    % (self.name, article_id, version)
                )
                return self.ACTIVITY_SUCCESS
            if not self.settings.epp_data_bucket:
                self.logger.info(
                    (
                        "epp_data_bucket in settings is blank, skipping %s "
                        "for article_id %s, version %s"
                    )
                    % (self.name, article_id, version)
                )
                return self.ACTIVITY_SUCCESS

            # generate preprint XML file
            try:
                xml_file_path = preprint.generate_preprint_xml(
                    self.settings,
                    article_id,
                    version,
                    self.name,
                    self.directories,
                    self.logger,
                )
            except preprint.PreprintArticleException as exception:
                self.logger.exception(
                    (
                        "%s, exception raised generating preprint XML"
                        " for article_id %s version %s: %s"
                    )
                    % (self.name, article_id, version, str(exception))
                )
                return self.ACTIVITY_PERMANENT_FAILURE
            except Exception as exception:
                self.logger.exception(
                    (
                        "%s, unhandled exception raised when generating preprint XML"
                        " for article_id %s version %s: %s"
                    )
                    % (self.name, article_id, version, str(exception))
                )
                return self.ACTIVITY_PERMANENT_FAILURE
        elif run:
            # download the preprint XML from the expanded folder
            storage = storage_context(self.settings)
            bucket_folder_name = expanded_folder_name.replace(os.sep, "/")
            bucket_resource = (
                self.settings.storage_provider
                + "://"
                + expanded_bucket_name
                + "/"
                + bucket_folder_name
            )
            s3_key_names = storage.list_resources(bucket_resource)
            # for now the only XML file is the one to download
            xml_filename = None
            for s3_key_name in s3_key_names:
                if s3_key_name.endswith(".xml"):
                    xml_filename = s3_key_name.split("/")[-1]
                    break
            # check if a file name was found
            if not xml_filename:
                self.logger.info(
                    "%s, xml_filename is None for article %s version %s"
                    % (self.name, article_id, version)
                )
                return self.ACTIVITY_PERMANENT_FAILURE

            # download the XML file
            xml_file_path = os.path.join(
                self.directories.get("INPUT_DIR"), xml_filename
            )
            with open(xml_file_path, "wb") as open_file:
                storage_resource_origin = bucket_resource + "/" + xml_filename
                self.logger.info(
                    "%s, downloading %s to %s"
                    % (self.name, storage_resource_origin, xml_file_path)
                )
                storage.get_resource_to_file(storage_resource_origin, open_file)

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
