from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_structure, utils
from activity.objects import Activity

"""
DepositAssets.py activity
"""


class activity_DepositAssets(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DepositAssets, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DepositAssets"
        self.pretty_name = "Deposit assets"
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
            "Depositing assets for " + article_id,
        )

        try:

            expanded_folder_name = session.get_value("expanded_folder")
            expanded_folder_bucket = (
                self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
            )

            storage = storage_context(self.settings)
            storage_provider = self.settings.storage_provider + "://"

            orig_resource = (
                storage_provider + expanded_folder_bucket + "/" + expanded_folder_name
            )
            files_in_bucket = storage.list_resources(orig_resource)
            # remove the subfolder name from file names
            files_in_bucket = [
                filename.rsplit("/", 1)[-1] for filename in files_in_bucket
            ]
            # filter figures that have already been copied (see DepositIngestAssets activity)
            pre_ingest_assets = article_structure.pre_ingest_assets(files_in_bucket)

            other_assets = [
                asset for asset in files_in_bucket if asset not in pre_ingest_assets
            ]

            # assets bucket
            cdn_bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
            )

            no_download_extensions = self.get_no_download_extensions(
                self.settings.no_download_extensions
            )

            for file_name in other_assets:
                orig_resource = (
                    storage_provider
                    + expanded_folder_bucket
                    + "/"
                    + expanded_folder_name
                    + "/"
                )
                dest_resource = (
                    storage_provider
                    + cdn_bucket_name
                    + "/"
                    + utils.pad_msid(article_id)
                    + "/"
                )

                storage.copy_resource(
                    orig_resource + file_name, dest_resource + file_name
                )

                if self.logger:
                    self.logger.info(
                        "Uploaded file %s to %s" % (file_name, cdn_bucket_name)
                    )

                file_name_no_extension, extension = file_name.rsplit(".", 1)
                if extension not in no_download_extensions:
                    content_type = utils.content_type_from_file_name(file_name)
                    dict_metadata = {
                        "Content-Disposition": str(
                            "Content-Disposition: attachment; filename="
                            + file_name
                            + ";"
                        ),
                        "Content-Type": content_type,
                    }
                    file_download = file_name_no_extension + "-download." + extension

                    # file is copied with additional metadata
                    storage.copy_resource(
                        orig_resource + file_name,
                        dest_resource + file_download,
                        additional_dict_metadata=dict_metadata,
                    )

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                "Deposited assets for article " + article_id,
            )

        except Exception as exception:
            self.logger.exception("Exception when Depositing assets")
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error depositing assets for article "
                + article_id
                + " message:"
                + str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        return self.ACTIVITY_SUCCESS

    def get_no_download_extensions(self, no_download_extensions):
        return [x.strip() for x in no_download_extensions.split(",")]
