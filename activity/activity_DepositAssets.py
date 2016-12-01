import activity
from boto.s3.connection import S3Connection
from provider.execution_context import Session
from provider.storage_provider import StorageContext
from mimetypes import guess_type

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

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, "Deposit assets", "start",
                                "Depositing assets for " + article_id)

        try:
            conn = S3Connection(self.settings.aws_access_key_id,
                                self.settings.aws_secret_access_key)

            expanded_folder_name = session.get_value(run, 'expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix +
                                      self.settings.expanded_bucket)

            expanded_bucket = conn.get_bucket(expanded_folder_bucket)
            cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket

            no_download_extensions = self.get_no_download_extensions(self.settings.no_download_extensions)

            storage_context = StorageContext(self.settings)
            storage_provider = self.settings.storage_provider + "://"
            published_bucket_path = self.settings.publishing_buckets_prefix + self.settings.published_bucket_path

            keys = self.get_keys(expanded_bucket, expanded_folder_name)
            for key in keys:
                (file_key, file_name) = key
                #file_key.copy(cdn_bucket_name, article_id + "/" + file_name)

                orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name + "/" + file_name
                dest_resource = storage_provider + cdn_bucket_name + "/" + article_id + "/" + file_name
                additional_dest_resource = storage_provider + published_bucket_path + "/" + article_id + "/" + file_name
                storage_context.copy_resource(orig_resource, dest_resource)
                storage_context.copy_resource(orig_resource, additional_dest_resource)

                if self.logger:
                    self.logger.info("Uploaded key %s to %s" % (file_name, cdn_bucket_name))
                file_name_no_extension, extension = file_name.rsplit('.', 1)
                if extension not in no_download_extensions:

                    content_type, encoding = guess_type(file_name)
                    dict_metadata = {'Content-Disposition':
                                     str("Content-Disposition: attachment; filename=" + file_name + ";"),
                                     'Content-Type': content_type}

                    dest_resource = storage_provider + cdn_bucket_name + "/" + article_id + "/" + \
                                    file_name_no_extension + "-download." + extension
                    additional_dest_resource = storage_provider + published_bucket_path + "/" + article_id + "/" + \
                                               file_name_no_extension + "-download." + extension
                    storage_context.copy_resource(orig_resource, dest_resource, additional_dict_metadata=dict_metadata)
                    storage_context.copy_resource(orig_resource, additional_dest_resource)




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

    def get_no_download_extensions(self, no_download_extensions):
        return [x.strip() for x in no_download_extensions.split(',')]

    @staticmethod
    def get_keys(bucket, expanded_folder_name):
        keys = []
        files = bucket.list(expanded_folder_name + "/", "/")
        for bucket_file in files:
            key = bucket.get_key(bucket_file.key)
            filename = key.name.rsplit('/', 1)[1]
            keys.append((key, filename))
        return keys
