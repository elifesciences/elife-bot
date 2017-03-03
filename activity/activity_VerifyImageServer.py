import activity
import json
from provider.execution_context import Session
from provider.storage_provider import StorageContext
import provider.article_structure as article_structure
import provider.iiif as iiif
import requests

"""
activity_VerifyImageServer.py activity
"""


class ValidationException(RuntimeError):
    pass


class activity_VerifyImageServer(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VerifyImageServer"
        self.pretty_name = "Verify Image Server"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Checks if original figure is valid when called via the IIIF standard using an Image server"
        self.logger = logger

    def do_activity(self, data=None):

        try:
            if self.logger:
                self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

            run = data['run']
            session = Session(self.settings)
            article_id = session.get_value(run, 'article_id')
            version = session.get_value(run, 'version')

        except Exception as e:
            self.logger.exception(str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        try:
            storage_context = StorageContext(self.settings)
            bucket = self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket
            images_resource = "".join((self.settings.storage_provider, "://", bucket, "/", article_id))

            files_in_bucket = storage_context.list_resources(images_resource)
            original_figures = article_structure.get_original_figures(files_in_bucket)

            iiif_path_for_article = self.settings.iiif_resolver.replace('{article_id}', article_id)

            results = self.retrieve_endpoints_check(original_figures, iiif_path_for_article)

            bad_images = list(filter(lambda x: x[0] == False, results))

            if len(bad_images) > 0:
                # print endpoints that did not work
                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                        "Some images are not available through the IIIF endpoint: " + str(bad_images))

                return activity.activity.ACTIVITY_PERMANENT_FAILURE

            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Finished Verification. All endpoints work. Article: " + article_id)
            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            self.logger.exception(str(e))
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "An error occurred when checking IIIF endpoint. Article " +
                                    article_id + '; message: ' + str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def retrieve_endpoints_check(self, original_figures, iiif_path_for_article):
        return list(map(lambda fig: iiif.try_endpoint(iiif.endpoint(self.settings, iiif_path_for_article, fig), self.logger),
                        original_figures))