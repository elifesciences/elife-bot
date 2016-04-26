import activity
from boto.s3.connection import S3Connection
from provider.execution_context import Session

"""
DepositAssets.py activity
"""


class activity_DepositAssets(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "DepositAssets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit assets"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """

        session = Session(self.settings)
        version = session.get_value(self.get_workflowId(), 'version')
        article_id = session.get_value(self.get_workflowId(), 'article_id')
        run = session.get_value(self.get_workflowId(), 'run')

        self.emit_monitor_event(self.settings, article_id, version, run, "Deposit assets", "start",
                                "Depositing assets for " + article_id)

        try:
            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)

            expanded_folder_name = session.get_value(self.get_workflowId(), 'expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix +
                                      self.settings.expanded_bucket)

            expanded_bucket = conn.get_bucket(expanded_folder_bucket)
            cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket

            no_download_extensions = [x.strip() for x in self.settings.no_download_extensions.split(',')]

            keys = self.get_keys(expanded_bucket, expanded_folder_name)
            for key in keys:
                (file_key, file_name) = key
                file_key.copy(cdn_bucket_name, article_id + "/" + file_name)
                if self.logger:
                    self.logger.info("Uploaded key %s to %s" % (file_name, cdn_bucket_name))
                file_name_no_extension, extension = file_name.rsplit('.', 1)
                if extension not in no_download_extensions:
                    download_metadata = file_key.metadata
                    download_metadata['Content-Disposition'] = str(
                        "Content-Disposition: attachment; filename=" + file_name + ";")
                    file_key.copy(cdn_bucket_name, article_id + "/" +
                                  file_name_no_extension + "-download." + extension,
                                  metadata=download_metadata)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Deposit assets", "end",
                                    "Deposited assets for article " + article_id)

        except Exception as e:
            self.logger.exception("Exception when Depositing assets")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    "Deposit assets", "error",
                                    "Error depositing assets for article " + article_id +
                                    " message:" + e.message)
            return False

        return True

    @staticmethod
    def get_keys(bucket, expanded_folder_name):
        keys = []
        files = bucket.list(expanded_folder_name + "/", "/")
        for bucket_file in files:
            key = bucket.get_key(bucket_file.key)
            filename = key.name.rsplit('/', 1)[1]
            keys.append((key, filename))
        return keys
