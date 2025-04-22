import json
from provider.execution_context import get_session
from provider import outbox_provider, preprint, utils
from activity.objects import Activity


class activity_CleanOutbox(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_CleanOutbox, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "CleanOutbox"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Move file from the S3 outbox folder to a published folder"

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket

        # Track the success of some steps
        self.statuses = {
            "outbox_status": None,
            "clean_status": None,
            "activity_status": None,
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # Set date_stamp
        date_stamp = utils.set_datestamp()

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")
        version = session.get_value("version")

        # determine the outbox name
        # note: configured for FinishPreprintPublication only so far
        workflow_name = "FinishPreprintPublication"
        outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder(workflow_name)
        )
        published_folder = outbox_provider.published_folder(
            self.s3_bucket_folder(workflow_name)
        )

        if outbox_folder is None or published_folder is None:
            # fail the workflow if no outbox folders are found
            self.logger.error(
                "%s, version DOI %s outbox_folder %s, published_folder %s, failing the workflow"
                % (self.name, version_doi, outbox_folder, published_folder)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.statuses["outbox_status"] = True

        # generate list of outbox file names

        # generate preprint XML outbox file name
        # note: configured for preprint XML file names so far
        key_name = preprint.xml_filename(article_id, self.settings, version=version)
        published_file_names = [outbox_folder + key_name]

        self.logger.info(
            "%s, version DOI %s published_file_names: %s"
            % (self.name, version_doi, published_file_names)
        )

        # check files exist in the outbox
        outbox_s3_key_names = outbox_provider.get_outbox_s3_key_names(
            self.settings, self.publish_bucket, outbox_folder
        )

        self.logger.info(
            "%s, outbox_folder %s outbox_s3_key_names: %s"
            % (self.name, outbox_folder, outbox_s3_key_names)
        )

        # check files exist in the bucket folder
        approved_file_names = [
            file_name
            for file_name in published_file_names
            if file_name in outbox_s3_key_names
        ]

        self.logger.info(
            "%s, version DOI %s approved_file_names: %s"
            % (self.name, version_doi, approved_file_names)
        )

        if not approved_file_names:
            self.logger.info(
                "%s, version DOI %s, no published files found in the outbox"
                % (self.name, version_doi)
            )
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            self.clean_tmp_dir()
            return self.ACTIVITY_SUCCESS

        # Clean up outbox
        self.logger.info(
            "%s, moving files from outbox folder to published folder" % self.name
        )

        to_folder = outbox_provider.get_to_folder_name(
            published_folder, date_stamp
        )
        self.logger.info(
            "%s, version DOI %s to_folder: %s" % (self.name, version_doi, to_folder)
        )

        outbox_provider.clean_outbox(
            self.settings,
            self.publish_bucket,
            outbox_folder,
            to_folder,
            approved_file_names,
        )
        self.statuses["clean_status"] = True

        self.statuses["activity_status"] = True

        # Clean up disk
        self.clean_tmp_dir()

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        return self.ACTIVITY_SUCCESS
