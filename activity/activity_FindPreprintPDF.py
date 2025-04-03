import json
from provider import preprint, utils
from provider.execution_context import get_session
from activity.objects import Activity


class activity_FindPreprintPDF(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindPreprintPDF, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindPreprintPDF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Check whether a PDF exists for the preprint version and"
            " save its URL to the session"
        )

        self.statuses = {}

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "reviewed_preprint_api_endpoint"):
            self.logger.info(
                "%s, reviewed_preprint_api_endpoint in settings is missing, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.reviewed_preprint_api_endpoint:
            self.logger.info(
                "%s, reviewed_preprint_api_endpoint in settings is blank, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_id = session.get_value("article_id")
        version = session.get_value("version")

        # take the pdf_url value from data if specified
        if data.get("pdf_url"):
            session.store_value("pdf_url", data.get("pdf_url"))
            self.logger.info(
                "%s, from workflow input data got pdf_url %s"
                % (self.name, data.get("pdf_url"))
            )
            return self.ACTIVITY_SUCCESS
        # if not, look iup the pdf_url from the API endpoint

        # format the API endpoint URL
        url = self.settings.reviewed_preprint_api_endpoint.format(
            article_id=utils.pad_msid(article_id), version=version
        )
        self.logger.info("%s, get url %s" % (self.name, url))

        # check if PDF exists according to the API
        try:
            pdf_url = preprint.get_preprint_pdf_url(
                url,
                self.name,
                user_agent=getattr(self.settings, "user_agent", None),
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception raised getting pdf_url from endpoint %s: %s"
                % (self.name, url, str(exception))
            )
            pdf_url = None

        self.logger.info(
            "%s, for article_id %s version %s got pdf_url %s"
            % (self.name, article_id, version, pdf_url)
        )

        # save the pdf_url into the session
        session.store_value("pdf_url", pdf_url)

        return self.ACTIVITY_SUCCESS
