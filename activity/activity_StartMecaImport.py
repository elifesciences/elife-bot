import json
from provider import cleaner, requests_provider, utils
from provider.execution_context import get_session
from activity.objects import Activity


class activity_StartMecaImport(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_StartMecaImport, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "StartMecaImport"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Start a temporal workflow by endpoint POST to import MECA files"
        )

        self.statuses = {}

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)

        # check for required settings
        if not hasattr(self.settings, "meca_import_endpoint"):
            self.logger.info(
                "%s, meca_import_endpoint in settings is missing, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.meca_import_endpoint:
            self.logger.info(
                "%s, meca_import_endpoint in settings is blank, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS
        endpoint_url = self.settings.meca_import_endpoint

        # load session data
        version_doi = session.get_value("version_doi")
        doi, version = utils.version_doi_parts(version_doi)
        article_id = utils.msid_from_doi(doi)

        # specify the endpoint authentication
        auth = None
        if getattr(self.settings, "meca_import_auth_username") and getattr(
            self.settings, "meca_import_auth_password"
        ):
            auth = (
                getattr(self.settings, "meca_import_auth_username"),
                getattr(self.settings, "meca_import_auth_password"),
            )

        # assemble data to be posted to endpoint
        data = {
            "docmap": cleaner.docmap_url(self.settings, article_id),
            "temporalNamespace": getattr(
                self.settings, "meca_import_temporal_namespace"
            ),
            "workflowIdPrefix": getattr(
                self.settings, "meca_import_workflow_id_prefix"
            ),
        }
        self.logger.info(
            "%s, data to post for version DOI %s: %s" % (self.name, version_doi, data)
        )

        # POST to the endpoint
        self.logger.info(
            "%s, posting data version DOI %s to endpoint %s"
            % (self.name, version_doi, endpoint_url)
        )

        try:
            requests_provider.post_to_endpoint(
                endpoint_url,
                json.dumps(data),
                self.logger,
                self.name,
                content_type="application/json",
                user_agent=getattr(self.settings, "user_agent", None),
                auth=auth,
            )
            self.statuses["post"] = True
        except Exception as exception:
            self.logger.exception(
                "%s exception raised in POST to endpoint_url %s for version DOI %s: %s"
                % (self.name, endpoint_url, version_doi, str(exception))
            )
            return self.ACTIVITY_SUCCESS

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        return self.ACTIVITY_SUCCESS
