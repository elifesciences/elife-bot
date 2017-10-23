import activity
from boto.s3.connection import S3Connection
from provider.execution_context import Session
from provider.storage_provider import storage_context
from provider import article_structure

"""
DepositIngestAssets.py activity
"""


class activity_DepositIngestAssets(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

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

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Depositing Ingest assets for " + article_id)

        try:

            expanded_folder_name = session.get_value(run, 'expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix +
                                      self.settings.expanded_bucket)

            cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket

            storage_context = storage_context(self.settings)
            storage_provider = self.settings.storage_provider + "://"

            orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name
            files_in_bucket = storage_context.list_resources(orig_resource)

            pre_ingest_assets = article_structure.pre_ingest_assets(files_in_bucket)

            for file_name in pre_ingest_assets:

                orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name + "/" + file_name
                dest_resource = storage_provider + cdn_bucket_name + "/" + article_id + "/" + file_name
                storage_context.copy_resource(orig_resource, dest_resource)

                if self.logger:
                    self.logger.info("Uploaded file %s to %s" % (file_name, cdn_bucket_name))

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end",
                                    "Deposited Ingest assets for article " + article_id)
            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception("Exception when Depositing Ingest assets")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error depositing Ingest assets for article " + article_id +
                                    " message:" + e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE




