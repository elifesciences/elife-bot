import json
import provider.digest_provider as digest_provider
from activity.objects import Activity


class activity_CreateDigestMediumPost(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_CreateDigestMediumPost, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "CreateDigestMediumPost"
        self.pretty_name = "Create Digest Medium Post"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Create a post on Medium for a digest.")

        self.statuses = {}

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section,
            self.settings.digest_config_file)

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # get data
        (success, run, article_id, version,
         status, expanded_folder, run_type) = self.parse_data(data)
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
            # TODO
            # check is the first VoR version and not a silent correction
            # create the digest content from the docx and JATS file
            # POST to the Medium API endpoint
            pass

        except Exception as exception:
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))

        self.emit_end_message(article_id, version, run)

        return self.ACTIVITY_SUCCESS

    def parse_data(self, data):
        "extract individual values from the activity data"
        run = None
        article_id = None
        version = None
        status = None
        expanded_folder = None
        run_type = None
        success = None
        try:
            run = data.get("run")
            article_id = data.get("article_id")
            version = data.get("version")
            status = data.get("status")
            expanded_folder = data.get("expanded_folder")
            run_type = data.get("run_type")
            success = True
        except (TypeError, KeyError) as exception:
            self.logger.exception("Exception parsing the input data in %s." +
                                  " Details: %s" % self.pretty_name, str(exception))
        return success, run, article_id, version, status, expanded_folder, run_type

    def emit_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, status, message)
            return True
        except Exception as exception:
            self.logger.exception("Exception emitting %s message. Details: %s" %
                                  (str(status), str(exception)))

    def emit_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_message(
            article_id, version, run, "start",
            "Starting %s for %s" % (self.pretty_name, article_id))

    def emit_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_message(
            article_id, version, run, "end",
            "Finished %s for %s. Statuses: %s" % (self.pretty_name, article_id, self.statuses))

    def emit_error_message(self, article_id, version, run, message):
        "emit an error message to the queue"
        return self.emit_message(
            article_id, version, run, "error", message)
