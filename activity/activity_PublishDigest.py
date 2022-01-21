import json
import provider.digest_provider as digest_provider
from activity.objects import Activity


class activity_PublishDigest(Activity):
    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_PublishDigest, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "PublishDigest"
        self.pretty_name = "Publish the Digest via the API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Set digest as published, related to the research article,"
            + " if the digest not already published."
        )

        # Track the success of some steps
        self.statuses = {"approve": None, "put": None}

        # Digest JSON content
        self.digest_content = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section, self.settings.digest_config_file
        )

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # get data
        (success, run, article_id, version, status) = self.parse_data(data)
        if success is not True:
            self.logger.error("Failed to parse data in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE
        # emit start message
        success = self.emit_start_message(article_id, version, run)
        if success is not True:
            self.logger.error("Failed to emit a start message in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # Wrap in an exception during testing phase
        try:
            # Approve for ingestion
            self.statuses["approve"] = self.approve(article_id, status)
            if self.statuses.get("approve") is not True:
                self.logger.info(
                    "Digest for article %s was not approved for publish" % article_id
                )
                self.emit_end_message(article_id, version, run)
                return self.ACTIVITY_SUCCESS

            # get existing digest data
            digest_id = article_id
            existing_digest_json = digest_provider.get_digest_preview(
                digest_id, self.settings
            )
            if not existing_digest_json:
                self.logger.info(
                    "There is no existing digest for digest_id %s" % str(digest_id)
                )
                self.emit_end_message(article_id, version, run)
                return self.ACTIVITY_SUCCESS

            # set the stage attribute if is not published
            put_digest = False
            if existing_digest_json.get("stage") != "published":
                self.digest_content = digest_provider.set_stage(
                    existing_digest_json, "published"
                )
                self.logger.info(
                    "Set Digest stage value of %s to published" % article_id
                )
                if not self.digest_content.get("published"):
                    self.digest_content[
                        "published"
                    ] = digest_provider.published_date_from_lax(
                        self.settings, digest_id
                    )
                put_digest = True
            if not existing_digest_json.get("published"):
                # if published of the existing digest is not set, set it to the date published
                if not self.digest_content:
                    self.digest_content = existing_digest_json
                # set the published date
                self.digest_content[
                    "published"
                ] = digest_provider.published_date_from_lax(self.settings, digest_id)
                put_digest = True

            if put_digest:
                put_response = digest_provider.put_digest_to_endpoint(
                    self.logger, digest_id, self.digest_content, self.settings
                )
                self.statuses["put"] = True
                self.logger.info(
                    "Put Digest for %s to the endpoint, response: %s"
                    % (article_id, put_response)
                )
            else:
                self.logger.info(
                    "Digest is already published, did not put Digest for %s to the endpoint"
                    % article_id
                )

        except Exception as exception:
            self.logger.exception(
                "Exception raised in do_activity. Details: %s" % str(exception)
            )

        self.logger.info(
            "%s for article_id %s statuses: %s"
            % (self.name, str(article_id), self.statuses)
        )

        self.emit_end_message(article_id, version, run)

        return self.ACTIVITY_SUCCESS

    def parse_data(self, data):
        "extract individual values from the activity data"
        run = None
        article_id = None
        version = None
        status = None
        success = None
        try:
            run = data.get("run")
            article_id = data.get("article_id")
            version = data.get("version")
            status = data.get("status")
            success = True
        except (TypeError, KeyError) as exception:
            self.logger.exception(
                "Exception parsing the input data in %s."
                + " Details: %s" % self.pretty_name,
                str(exception),
            )
        return success, run, article_id, version, status

    def emit_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                status,
                message,
            )
            return True
        except Exception as exception:
            self.logger.exception(
                "Exception emitting %s message. Details: %s"
                % (str(status), str(exception))
            )

    def emit_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_message(
            article_id,
            version,
            run,
            "start",
            "Starting ingest digest to endpoint for %s" % article_id,
        )

    def emit_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_message(
            article_id,
            version,
            run,
            "end",
            "Finished ingest digest to endpoint for %s. Statuses: %s"
            % (article_id, self.statuses),
        )

    def emit_error_message(self, article_id, version, run, message):
        "emit an error message to the queue"
        return self.emit_message(article_id, version, run, "error", message)

    def approve(self, article_id, status):
        "should we ingest based on some basic attributes"
        approve_status = True
        # check by status
        return_status = digest_provider.approve_by_status(
            self.logger, article_id, status
        )
        if return_status is False:
            approve_status = return_status
        return approve_status
