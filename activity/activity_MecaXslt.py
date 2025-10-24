import os
import json
import time
from provider import meca
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


# session variable name to store the number of attempts
SESSION_ATTEMPT_COUNTER_NAME = "meca_xslt_attempt_count"

# maximum endpoint request attempts
MAX_ATTEMPTS = 4

# time in seconds to sleep between endpoint request attempts
SLEEP_SECONDS = 10


class activity_MecaXslt(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaXslt, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaXslt"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Apply XSL transformation to MECA XML"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {}

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        run_type = session.get_value("run_type")

        # check for required settings
        if run_type == "silent-correction":
            if not hasattr(self.settings, "meca_xsl_silent_endpoint"):
                self.logger.info(
                    "%s, meca_xsl_silent_endpoint in settings is missing, skipping"
                    % self.name
                )
                return self.ACTIVITY_SUCCESS
            if not self.settings.meca_xsl_silent_endpoint:
                self.logger.info(
                    "%s, meca_xsl_silent_endpoint in settings is blank, skipping"
                    % self.name
                )
                return self.ACTIVITY_SUCCESS
            endpoint_url = self.settings.meca_xsl_silent_endpoint
        else:
            if not hasattr(self.settings, "meca_xsl_endpoint"):
                self.logger.info(
                    "%s, meca_xsl_endpoint in settings is missing, skipping" % self.name
                )
                return self.ACTIVITY_SUCCESS
            if not self.settings.meca_xsl_endpoint:
                self.logger.info(
                    "%s, meca_xsl_endpoint in settings is blank, skipping" % self.name
                )
                return self.ACTIVITY_SUCCESS
            endpoint_url = self.settings.meca_xsl_endpoint

        self.make_activity_directories()

        # load session data
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

        # POST to the endpoint
        self.logger.info(
            "%s, posting %s to endpoint %s" % (self.name, xml_file_path, endpoint_url)
        )
        response_content = meca.post_to_endpoint(
            xml_file_path,
            endpoint_url,
            getattr(self.settings, "user_agent", None),
            self.name,
            self.logger,
        )

        if response_content:
            self.statuses["post"] = True
        else:
            self.logger.exception(
                "%s no response content from POST to endpoint_url %s of file %s"
                % (self.name, endpoint_url, xml_file_path)
            )

            # count the number of attempts
            if not session.get_value(SESSION_ATTEMPT_COUNTER_NAME):
                session.store_value(SESSION_ATTEMPT_COUNTER_NAME, 1)
            else:
                # increment
                session.store_value(
                    SESSION_ATTEMPT_COUNTER_NAME,
                    int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) + 1,
                )
                self.logger.info(
                    "%s, POST to endpoint_url attempts for file %s: %s"
                    % (
                        self.name,
                        xml_file_path,
                        session.get_value(SESSION_ATTEMPT_COUNTER_NAME),
                    )
                )

            if int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) < MAX_ATTEMPTS:
                # Clean up disk
                self.clean_tmp_dir()
                # sleep a short time
                time.sleep(SLEEP_SECONDS)
                # return a temporary failure
                return self.ACTIVITY_TEMPORARY_FAILURE
            if int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) >= MAX_ATTEMPTS:
                # maximum number of attempts are completed
                self.logger.exception(
                    "%s, POST to endpoint_url %s attempts reached MAX_ATTEMPTS of %s for file %s"
                    % (self.name, endpoint_url, MAX_ATTEMPTS, xml_file_path)
                )
                self.clean_tmp_dir()
                return self.ACTIVITY_PERMANENT_FAILURE

        # save the response content to S3
        s3_resource = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, updating transformed XML to %s" % (self.name, s3_resource)
        )
        storage.set_resource_from_string(s3_resource, response_content)
        self.statuses["upload"] = True

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        return self.ACTIVITY_SUCCESS
