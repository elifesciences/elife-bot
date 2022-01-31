from provider.execution_context import get_session
from provider import fastly_provider
from activity.objects import Activity

"""
activity_InvalidateCdn.py activity
"""


class activity_InvalidateCdn(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_InvalidateCdn, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "InvalidateCdn"
        self.pretty_name = "Fastly Invalidate Cdn"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Runs Fastly purge request on CDN."
        self.logger = logger

    def do_activity(self, data):
        try:
            run = data["run"]
            session = get_session(self.settings, data, run)
            article_id = session.get_value("article_id")
            version = session.get_value("version")
        except Exception as e:
            self.logger.error(
                "Error retrieving basic article data. Data: %s, Exception: %s"
                % (str(data), str(e))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "start",
                "Starting Fastly purge API calls.",
            )
            fastly_responses = fastly_provider.purge(article_id, version, self.settings)
            self.logger.info(
                "Fastly responses: %s",
                [(r.status_code, r.content) for r in fastly_responses],
            )

            dashboard_message = (
                "Fastly purge API calls performed for article %s." % str(article_id)
            )
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "end",
                dashboard_message,
            )
            return self.ACTIVITY_SUCCESS

        except Exception as e:
            error_message = str(e)
            self.logger.error(error_message)
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                error_message,
            )
            return self.ACTIVITY_PERMANENT_FAILURE
