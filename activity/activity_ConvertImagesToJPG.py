import activity
import json
from provider.execution_context import Session
from provider.storage_provider import StorageContext
import provider.article_structure as article_structure
import provider.image_conversion as image_conversion
import os



class activity_ConvertImagesToJPG(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

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
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting submission convert images to jpg for article " + article_id)

        try:
            expanded_folder_name = session.get_value(run, 'expanded_folder')
            expanded_folder_bucket = (self.settings.publishing_buckets_prefix +
                                      self.settings.expanded_bucket)
            storage_provider = self.settings.storage_provider + "://"
            orig_resource = storage_provider + expanded_folder_bucket + "/" + expanded_folder_name

            storage_context = StorageContext(self.settings)
            files_in_bucket = storage_context.list_resources(orig_resource)

            figures = filter(article_structure.article_figure, files_in_bucket)

            formats = {"Original": {
                            "sources": "tif",
                            "format": "jpg",
                            "resolution": 96,
                            "download": "yes"
                        }}

            for file_name in figures:
                figure_resource = orig_resource + "/" + file_name
                file_path = self.get_tmp_dir() + os.sep + file_name
                file_pointer = storage_context.get_resource_to_file_pointer(figure_resource, file_path)

                cdn_bucket_name = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
                cdn_resource_path = storage_provider + cdn_bucket_name + "/" + article_id + "/"
                published_bucket_path = self.settings.publishing_buckets_prefix + self.settings.published_bucket + '/articles'
                add_resource_path = storage_provider + published_bucket_path + "/" + article_id + "/"

                publish_locations = [cdn_resource_path, add_resource_path]

                image_conversion.generate_images(self.settings, formats, file_pointer, article_structure.ArticleInfo(file_name),
                                                 publish_locations, self.logger)

            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Finished converting images for " + article_id + ": " +
                                    str(len(files_in_bucket)) + " images processed ")
            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception("An error occurred during " + self.pretty_name)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error converting images to JPG for article" + article_id +
                                    " message:" + e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE
