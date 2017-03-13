import activity
import json
from provider.execution_context import Session
from provider.storage_provider import StorageContext
import time
import provider.glencoe_check as glencoe_check
import os


"""
activity_CopyGlencoeStillImages.py activity
"""


class ValidationException(RuntimeError):
    pass

class activity_CopyGlencoeStillImages(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "CopyGlencoeStillImages"
        self.pretty_name = "Copy Glencoe Still Images"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Copies the Glencoe video still images to the CDN bucket"
        self.logger = logger

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            run = data['run']
            session = Session(self.settings)
            article_id = session.get_value(run, 'article_id')
            version = session.get_value(run, 'version')
        except Exception as e:
            self.logger.exception(str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting check/copy of Glencoe video still images " + article_id)
        try:
            metadata = glencoe_check.metadata(glencoe_check.check_msid(article_id), self.settings)
            jpgs = glencoe_check.jpg_href_values(metadata)
            if len(jpgs) > 0:
                for jpg in jpgs:
                    self.store_file(jpg, article_id)

            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Finished Copying Glencoe still images to CDN. "
                                    "Article: " + article_id)

            return activity.activity.ACTIVITY_SUCCESS
        except Exception as e:
            self.logger.exception(str(e))
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "An error occurred when checking/copying Glencoe still images. Article " +
                                    article_id + '; message: ' + str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def s3_resource(self, path, article_id):
        filename = os.path.split(path)[1]
        return self.settings.storage_provider + "://" + \
               self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket + "/" + \
               article_id + "/" + filename

    def store_file(self, path, article_id):
        storage_context = StorageContext(self.settings)
        with open(path) as still_image:
            storage_context.set_resource_from_file(self.s3_resource(path, article_id), still_image)

