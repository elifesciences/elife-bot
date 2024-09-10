import os
import json
from provider import github_provider, meca
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_ValidatePreprintSchematron(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ValidatePreprintSchematron, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ValidatePreprintSchematron"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Validate preprint JATS XML against a Schematron"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {
            "download": None,
            "results": None,
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "preprint_schematron_endpoint"):
            self.logger.info(
                "%s, preprint_schematron_endpoint in settings is missing, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.preprint_schematron_endpoint:
            self.logger.info(
                "%s, preprint_schematron_endpoint in settings is blank, skipping"
                % self.name
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
        storage_resource_origin = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        self.statuses["download"] = True

        endpoint_url = self.settings.preprint_schematron_endpoint
        self.logger.info(
            "%s, posting %s to endpoint %s" % (self.name, xml_file_path, endpoint_url)
        )

        # POST to the endpoint
        response_content = meca.post_to_endpoint(
            xml_file_path,
            endpoint_url,
            getattr(self.settings, "user_agent", None),
            self.name,
            self.logger,
        )

        if response_content:
            # check response for errors and warnings
            errors, warnings = self.check_schematron_response_content(
                response_content, version_doi, xml_file_path
            )
            # format the validation message
            log_message = compose_validation_message(errors, warnings)
            self.logger.info(
                "%s, validation message for file %s: %s"
                % (self.name, xml_file_path, log_message)
            )
            # add github issue comment
            issue_comment = "```\n%s\n```" % log_message
            github_provider.add_github_issue_comment(
                self.settings, self.logger, self.name, version_doi, issue_comment
            )
        else:
            # failed to get a response
            log_message = (
                "%s, no response content from POST to endpoint_url %s of file %s"
                % (self.name, endpoint_url, xml_file_path)
            )
            self.logger.exception(log_message)
            # add github issue comment
            github_provider.add_github_issue_comment(
                self.settings, self.logger, self.name, version_doi, log_message
            )

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        self.clean_tmp_dir()

        return self.ACTIVITY_SUCCESS

    def check_schematron_response_content(
        self, response_content, version_doi, xml_file_path
    ):
        "look for response errors adn warnings"
        errors = []
        warnings = []
        # check for results
        response_json = json.loads(response_content)
        self.logger.info(
            "%s, validation results count %s for file %s"
            % (
                self.name,
                len(response_json.get("results", [])),
                xml_file_path,
            )
        )
        if response_json.get("results"):
            self.statuses["results"] = True
            errors = response_json.get("results").get("errors", [])
            warnings = response_json.get("results").get("warnings", [])
        else:
            # if no results log a message
            self.logger.info(
                "%s, error for version DOI %s file %s: %s"
                % (
                    self.name,
                    version_doi,
                    xml_file_path,
                    response_json,
                )
            )
        return errors, warnings


def compose_validation_message(errors, warnings):
    "format Schematron validation message to go into the Github issue comment"
    if not errors and not warnings:
        return "(No schematron messages)"
    log_messages = []
    for message in errors:
        log_messages.append("%s: %s" % (message.get("type"), message.get("message")))
    for message in warnings:
        log_messages.append("%s: %s" % (message.get("type"), message.get("message")))
    return "\n".join(log_messages)
