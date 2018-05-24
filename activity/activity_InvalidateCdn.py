import activity
from provider import cloudfront_provider, fastly_provider
from boto.cloudfront.exception import CloudFrontServerError

"""
activity_InvalidateCdn.py activity
"""

class activity_InvalidateCdn(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "InvalidateCdn"
        self.pretty_name = "CloudFront Invalidate Cdn"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Runs CloudFront Invalidation request on Cdn bucket."
        self.logger = logger

    def do_activity(self, data):
        try:
            article_id = data['article_id']
            version = data['version']
            run = data['run']
        except Exception as e:
            self.logger.error("Error retrieving basic article data. Data: %s, Exception: %s" % (str(data), str(e)))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        try:

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start", "Starting check for generation of pdf cover.")

            ### If we want to run Invalidation only if CDN has been previously populated
            # if "files_in_cdn" in data:
            #     if data["files_in_cdn"] == True:
            #         cloudfront_provider.create_invalidation(article_id)
            #         dashboard_message = "CloudFront Invalidation command sent for article %s." % str(article_id)
            #     else:
            #         dashboard_message = "CloudFront Invalidation was not necessary for article %s." % str(article_id)
            try: 
                cloudfront_provider.create_invalidation(article_id, self.settings)
            except CloudFrontServerError as e:
                if e.error_code == 'TooManyInvalidationsInProgress':
                    self.logger.warning(e)
                    self.emit_monitor_event(
                        self.settings,
                        article_id, 
                        version,
                        run,
                        self.pretty_name,
                        "error",
                        "Too many CloudFront invalidations in progress; message: " + str(e)
                    )
                    return activity.activity.ACTIVITY_TEMPORARY_FAILURE
                raise

            fastly_response = fastly_provider.purge(article_id, self.settings)
            self.logger.info("Fastly response: %s\n%s", fastly_response.status_code, fastly_response.content)

            dashboard_message = "CloudFront Invalidation command sent for article %s." % str(article_id)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end", dashboard_message)
            return activity.activity.ACTIVITY_SUCCESS

        except Exception as e:
            error_message = str(e)
            self.logger.error(error_message)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error", error_message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE




