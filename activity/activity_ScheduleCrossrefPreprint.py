import json
import os
import shutil
from provider import outbox_provider, preprint, utils
from provider.storage_provider import storage_context
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
            # get data from the session
            run = data["run"]
            session = get_session(self.settings, data, run)
            article_id = session.get_value("article_id")
            version = session.get_value("version")
            article_xml_path = session.get_value("article_xml_path")
            expanded_folder = session.get_value("expanded_folder")
        except:
            self.logger.exception("Error starting %s activity" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info("%s, article_id: %s" % (self.name, article_id))
        self.logger.info("%s, version: %s" % (self.name, version))

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # local path to the article XML file
        input_xml_file_path = os.path.join(
            self.directories.get("INPUT_DIR"), article_xml_path
        )
        # create folders if they do not exist
        os.makedirs(os.path.dirname(input_xml_file_path), exist_ok=True)

        # download XML from the bucket folder
        orig_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        storage_resource_origin = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, storage_resource_origin, input_xml_file_path)
        )
        try:
            with open(input_xml_file_path, "wb") as open_file:
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except Exception as exception:
            self.logger.exception(
                "%s, input_xml_file_path is None for article %s version %s: %s"
                % (self.name, article_id, version, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # rename the file
        xml_file_name = preprint.PREPRINT_XML_FILE_NAME_PATTERN.format(
            article_id=utils.pad_msid(article_id), version=version
        )
        xml_file_path = input_xml_file_path.replace(
            input_xml_file_path.rsplit(os.sep, 1)[-1], xml_file_name
        )
        self.logger.info(
            "%s, moving %s to %s for article %s version %s"
            % (self.name, input_xml_file_path, xml_file_path, article_id, version)
        )
        shutil.move(input_xml_file_path, xml_file_path)

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
