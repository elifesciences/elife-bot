from boto.s3.connection import S3Connection
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_structure, utils
from activity.objects import Activity

"""
DepositIngestAssets.py activity
"""


class activity_DepositIngestAssets(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DepositIngestAssets, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DepositIngestAssets"
        self.pretty_name = "Deposit Ingest Assets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit Ingest Assets (Pre-Ingest)"
        self.logger = logger

    def do_activity(self, data=None):

        run = data["run"]
        session = get_session(self.settings, data, run)
        version = session.get_value("version")
        article_id = session.get_value("article_id")

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            self.pretty_name,
            "start",
            "Depositing Ingest assets for " + article_id,
        )

        try:

            expanded_folder_name = session.get_value("expanded_folder")
            expanded_folder_bucket = (
                self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
            )

            cdn_bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
            )

            storage = storage_context(self.settings)
            storage_provider = self.settings.storage_provider + "://"

            orig_resource = (
                storage_provider + expanded_folder_bucket + "/" + expanded_folder_name
            )
            files_in_bucket = storage.list_resources(orig_resource)
            # remove the subfolder name from file names
            files_in_bucket = [filename.rsplit("/", 1)[-1] for filename in files_in_bucket]
            pre_ingest_assets = article_structure.pre_ingest_assets(files_in_bucket)

            for file_name in pre_ingest_assets:

                orig_resource = (
                    storage_provider
                    + expanded_folder_bucket
                    + "/"
                    + expanded_folder_name
                    + "/"
                    + file_name
                )
                dest_resource = (
                    storage_provider
                    + cdn_bucket_name
                    + "/"
                    + utils.pad_msid(article_id)
                    + "/"
                    + file_name
                )
                storage.copy_resource(orig_resource, dest_resource)

                if self.logger:
                    self.logger.info(
                        "Uploaded file %s to %s" % (file_name, cdn_bucket_name)
                    )

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                "Deposited Ingest assets for article " + article_id,
            )
            return self.ACTIVITY_SUCCESS

        except Exception as exception:
            self.logger.exception("Exception when Depositing Ingest assets")
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error depositing Ingest assets for article "
                + article_id
                + " message:"
                + str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE
