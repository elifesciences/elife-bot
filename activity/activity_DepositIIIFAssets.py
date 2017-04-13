import activity
from boto.s3.connection import S3Connection
from provider.execution_context import Session
from provider.storage_provider import StorageContext
from provider import article_structure

"""
DepositIIIFAssets.py activity
"""


class activity_DepositIIIFAssets(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "DepositIIIFAssets"
        self.pretty_name = "Deposit IIIF Assets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit IIIF assets"
        self.logger = logger

    def do_activity(self, data=None):

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Depositing IIIF assets for " + article_id)

        try:

            expanded_folder_name = session.get_value(run, 'expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix +
                                      self.settings.expanded_bucket)

            cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket

            storage_context = StorageContext(self.settings)
            storage_provider = self.settings.storage_provider + "://"

            orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name
            files_in_bucket = storage_context.list_resources(orig_resource)
            original_figures = article_structure.get_figures_for_iiif(files_in_bucket)
            original_figures_and_videos = original_figures + article_structure.get_videos(files_in_bucket)

            published_bucket_path = self.settings.publishing_buckets_prefix + self.settings.published_bucket + '/articles'

            for file_name in original_figures_and_videos:

                orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name + "/" + file_name
                dest_resource = storage_provider + cdn_bucket_name + "/" + article_id + "/" + file_name
                additional_dest_resource = storage_provider + published_bucket_path + "/" + article_id + "/" + file_name
                storage_context.copy_resource(orig_resource, dest_resource)
                storage_context.copy_resource(orig_resource, additional_dest_resource)

                if self.logger:
                    self.logger.info("Uploaded file %s to %s and %s" % (file_name, cdn_bucket_name,
                                                                        published_bucket_path))

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end",
                                    "Deposited IIIF assets for article " + article_id)
            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception("Exception when Depositing IIIF assets")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error depositing IIIF assets for article " + article_id +
                                    " message:" + e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE




