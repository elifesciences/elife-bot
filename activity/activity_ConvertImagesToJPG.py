import os
from activity.objects import Activity
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_structure, image_conversion, utils


class activity_ConvertImagesToJPG(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ConvertImagesToJPG, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ConvertImagesToJPG"
        self.pretty_name = "Convert Images To JPG"
        self.version = "1"

        # standard bot activity parameters
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Converts article images to JPG"
        self.logger = logger

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

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
            "Starting submission convert images to jpg for article " + article_id,
        )

        try:
            expanded_folder_name = session.get_value("expanded_folder")
            expanded_folder_bucket = (
                self.settings.publishing_buckets_prefix + self.settings.expanded_bucket
            )
            storage_provider = self.settings.storage_provider + "://"
            orig_resource = (
                storage_provider + expanded_folder_bucket + "/" + expanded_folder_name
            )

            storage = storage_context(self.settings)
            files_in_bucket = storage.list_resources(orig_resource)

            figures = []
            figures += list(filter(article_structure.article_figure, files_in_bucket))
            figures += list(filter(article_structure.inline_figure, files_in_bucket))

            # download is not a IIIF asset but is currently kept for compatibility
            # download may become obsolete in future
            formats = {
                "Original": {"sources": "tif", "format": "jpg", "download": "yes"}
            }

            for file_name in figures:
                figure_resource = orig_resource + "/" + file_name
                file_path = self.get_tmp_dir() + os.sep + file_name
                file_pointer = storage.get_resource_to_file_pointer(
                    figure_resource, file_path
                )

                cdn_bucket_name = (
                    self.settings.publishing_buckets_prefix
                    + self.settings.ppp_cdn_bucket
                )
                cdn_resource_path = (
                    storage_provider
                    + cdn_bucket_name
                    + "/"
                    + utils.pad_msid(article_id)
                    + "/"
                )

                publish_locations = [cdn_resource_path]

                image_conversion.generate_images(
                    self.settings,
                    formats,
                    file_pointer,
                    article_structure.ArticleInfo(file_name),
                    publish_locations,
                    self.logger,
                )

            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                "Finished converting images for "
                + article_id
                + ": "
                + str(len(figures))
                + " images processed ",
            )
            self.clean_tmp_dir()
            return Activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception("An error occurred during " + self.pretty_name)
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error converting images to JPG for article"
                + article_id
                + " message:"
                + str(e),
            )
            return Activity.ACTIVITY_PERMANENT_FAILURE
