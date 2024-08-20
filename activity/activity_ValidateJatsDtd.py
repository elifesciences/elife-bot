import os
import json
from provider import github_provider, meca
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_ValidateJatsDtd(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidateJatsDtd, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ValidateJatsDtd"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Validate JATS XML against a DTD"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {}

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "meca_dtd_endpoint"):
            self.logger.info(
                "%s, meca_dtd_endpoint in settings is missing, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.meca_dtd_endpoint:
            self.logger.info(
                "%s, meca_dtd_endpoint in settings is blank, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS

        self.make_activity_directories()

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        article_xml_path = session.get_value("article_xml_path")
        expanded_folder = session.get_value("expanded_folder")
        version_doi = session.get_value("version_doi")

        storage = storage_context(self.settings)

        # local path to the article XML file
        xml_file_path = os.path.join(
            self.directories.get("INPUT_DIR"), article_xml_path
        )

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        orig_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # download XML from the bucket folder
        self.logger.info(
            "%s, downloading %s to %s" % (self.name, orig_resource, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage_resource_origin = orig_resource + "/" + article_xml_path
            storage.get_resource_to_file(storage_resource_origin, open_file)
        self.statuses["download"] = True

        endpoint_url = self.settings.meca_dtd_endpoint
        self.logger.info(
            "%s, posting %s to endpoint %s" % (self.name, xml_file_path, endpoint_url)
        )
        # POST to the DTD endpoint
        response_content = meca.post_to_endpoint(
            xml_file_path,
            endpoint_url,
            getattr(self.settings, "user_agent", None),
            self.name,
            self.logger,
        )

        if response_content:
            self.check_validation_response_content(
                response_content, session, version_doi, xml_file_path
            )
        else:
            self.logger.exception(
                "%s no response content from POST to endpoint_url %s of file %s"
                % (self.name, endpoint_url, xml_file_path)
            )
            self.clean_tmp_dir()
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        self.clean_tmp_dir()

        return self.ACTIVITY_SUCCESS

    def check_validation_response_content(
        self, response_content, session, version_doi, xml_file_path
    ):
        "look for valid or invalid response content"
        # check for status
        response_json = json.loads(response_content)
        self.logger.info(
            "%s, validation status %s of file %s"
            % (
                self.name,
                response_json.get("status"),
                xml_file_path,
            )
        )
        if response_json.get("status") == "valid":
            self.statuses["valid"] = True
        else:
            # if invalid, log the validation error message to the session
            log_message = "%s, validation error for version DOI %s file %s: %s" % (
                self.name,
                version_doi,
                xml_file_path,
                response_json.get("errors"),
            )
            self.logger.info(log_message)
            meca.log_to_session("\n%s" % log_message, session)
            # add as a Github issue comment
            if (
                hasattr(self.settings, "github_token")
                and hasattr(self.settings, "preprint_issues_repo_name")
                and self.settings.github_token
                and self.settings.preprint_issues_repo_name
            ):
                try:
                    issue = github_provider.find_github_issue(
                        self.settings.github_token,
                        self.settings.preprint_issues_repo_name,
                        version_doi,
                    )
                    if issue:
                        github_provider.add_github_comment(
                            issue, "elife-bot workflow message:\n\n%s" % log_message
                        )
                except Exception as exception:
                    self.logger.exception(
                        (
                            "%s, exception when adding a comment to Github "
                            "for version DOI %s file %s. Details: %s"
                        )
                        % (self.name, version_doi, xml_file_path, str(exception))
                    )
