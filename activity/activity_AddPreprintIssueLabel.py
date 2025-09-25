import json
from provider import github_provider
from provider.execution_context import get_session
from activity.objects import Activity


LABEL = "workflow run"


class activity_AddPreprintIssueLabel(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AddPreprintIssueLabel, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AddPreprintIssueLabel"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Add label to the preprint Github issue"

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        settings_result = self.check_required_settings()
        if settings_result:
            self.logger.info("%s, %s" % (self.name, settings_result))
            return self.ACTIVITY_SUCCESS

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        version_doi = session.get_value("version_doi")

        # find Github issue
        issue = None
        try:
            issue = github_provider.find_github_issue(
                self.settings.github_token,
                self.settings.preprint_issues_repo_name,
                version_doi,
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception finding Github issue for version DOI %s: %s"
                % (self.name, version_doi, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        if issue:
            # add label
            try:
                github_provider.add_label_to_github_issue(issue, LABEL)
                self.logger.info(
                    "%s, added label to Github issue found for version DOI %s"
                    % (self.name, version_doi)
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception adding label to Github issue for version DOI %s: %s"
                    % (self.name, version_doi, str(exception))
                )
                return self.ACTIVITY_PERMANENT_FAILURE
        else:
            self.logger.info(
                "%s, no open Github issue found for version DOI %s"
                % (self.name, version_doi)
            )

        return self.ACTIVITY_SUCCESS

    def check_required_settings(self):
        "check required settings exist and are non-blank"
        if not hasattr(self.settings, "github_token"):
            return "github_token in settings is missing, skipping"
        if not self.settings.github_token:
            return "github_token in settings is blank, skipping"
        if not hasattr(self.settings, "preprint_issues_repo_name"):
            return "preprint_issues_repo_name in settings is missing, skipping"
        if not self.settings.preprint_issues_repo_name:
            return "preprint_issues_repo_name in settings is blank, skipping"
