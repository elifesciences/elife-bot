import json
from provider.execution_context import get_session
from provider import doaj, lax_provider
from activity.objects import Activity


class activity_DepositDOAJ(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositDOAJ, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "DepositDOAJ"
        self.pretty_name = "POST article metadata to the DOAJ API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "POST article metadata to the DOAJ API endpoint"

        # Track the success of some steps
        self.statuses = {"download": None, "build": None, "post": None}

    def do_activity(self, data=None):
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # first check if there is an endpoint in the settings specified
        if not hasattr(self.settings, "doaj_endpoint"):
            self.logger.info("No doaj_endpoint in settings, skipping %s." % self.name)
            return self.ACTIVITY_SUCCESS
        if not self.settings.doaj_endpoint:
            self.logger.info(
                "doaj_endpoint in settings is blank, skipping %s." % self.name
            )
            return self.ACTIVITY_SUCCESS

        try:
            run = data["run"]
            session = get_session(self.settings, data, run)
            article_id = session.get_value("article_id")
        except Exception as exception:
            self.logger.exception(
                "Exception in %s getting article_id from session, run %s: %s" %
                (self.name, run, str(exception)),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # get JSON from Lax
        try:
            status_code, article_json_string = lax_provider.article_json(
                article_id, self.settings
            )
            article_json = json.loads(article_json_string)
            self.statuses["build"] = True
        except Exception as exception:
            self.logger.exception(
                "Exception in %s getting article json using lax_provider, article_id %s: %s" %
                (self.name, article_id, str(exception))
            )
            return self.ACTIVITY_TEMPORARY_FAILURE

        # check for VoR status
        if not article_json.get("status") == "vor":
            self.logger.info(
                "%s, article_id %s is not VoR status and will not be deposited"
                % (self.name, article_id)
            )
            return self.ACTIVITY_SUCCESS

        # convert Lax JSON to DOAJ JSON
        try:
            doaj_json = doaj.doaj_json(article_json, self.settings)
            self.logger.info("%s doaj_json for article_id %s: %s" % (self.name, article_id, doaj_json))
            self.statuses["download"] = True
        except Exception as exception:
            self.logger.exception(
                "Exception in %s building DOAJ json, article_id %s: %s" %
                (self.name, article_id, str(exception)),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # post to DOAJ endpoint
        try:
            response = doaj.doaj_post_request(
                self.settings.doaj_endpoint,
                article_id,
                doaj_json,
                self.settings.doaj_api_key,
            )
            self.statuses["post"] = True
        except Exception as exception:
            self.logger.exception(
                "Exception in %s posting to DOAJ API endpoint, article_id %s: %s" %
                (self.name, article_id, str(exception)),
            )
            return self.ACTIVITY_TEMPORARY_FAILURE

        self.logger.info(
            "%s for article_id %s statuses: %s" % (self.name, article_id, self.statuses)
        )

        return self.ACTIVITY_SUCCESS
