from provider.execution_context import get_session
from provider import fastly_provider
from activity.objects import Activity

"""
activity_InvalidatePreprintCdn.py activity
"""


class activity_InvalidatePreprintCdn(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_InvalidatePreprintCdn, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "InvalidatePreprintCdn"
        self.pretty_name = "Fastly Invalidate Preprint Cdn"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Runs Fastly purge request of preprint assets on CDN."
        self.logger = logger

    def do_activity(self, data):
        try:
            run = data["run"]
            session = get_session(self.settings, data, run)
            article_id = session.get_value("article_id")
            version = session.get_value("version")
        except Exception as exception:
            self.logger.error(
                "%s, Error retrieving basic article data. Data: %s, Exception: %s"
                % (self.name, str(data), str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info(
            "%s, Starting Fastly purge API calls for article_id %s version %s",
            self.name,
            article_id,
            version,
        )

        try:
            fastly_responses = fastly_provider.purge_preprint(
                article_id, version, self.settings
            )
            self.logger.info(
                "%s, Fastly responses: %s",
                self.name,
                [(r.status_code, r.content) for r in fastly_responses],
            )

            self.logger.info(
                "%s, Fastly purge API calls performed for article %s",
                self.name,
                str(article_id),
            )
            return self.ACTIVITY_SUCCESS

        except Exception as exception:
            self.logger.error(
                "%s, Error invalidating Fastly, Exception: %s",
                self.name,
                str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE
