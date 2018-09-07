import os
import json
from provider.storage_provider import storage_context
from provider.execution_context import get_session
import provider.digest_provider as digest_provider
from .activity import Activity


"""
activity_IngestDigestToEndpoint.py activity
"""


class activity_IngestDigestToEndpoint(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_IngestDigestToEndpoint, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "IngestDigestToEndpoint"
        self.pretty_name = "Ingest Digest to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Send Digest JSON to an API endpoint," +
                            " to be run when a research article is ingested")

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

        # Track the success of some steps
        self.approve_status = None

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        try:
            run = data["run"]
            session = get_session(self.settings, data, run)
            version = session.get_value("version")
            article_id = session.get_value("article_id")
            status = session.get_value("status")
            run_type = session.get_value("run_type")

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start",
                                    "Starting ingest digest to endpoint for " + article_id)
        except Exception as exception:
            self.logger.exception("Exception when getting the session for Starting ingest digest " +
                                  " to endpoint. Details: %s", str(exception))
            return self.ACTIVITY_PERMANENT_FAILURE

        # Approve for ingestion
        self.approve_status, error_message = self.approve(article_id, status, version, run_type)

        # bucket name
        bucket_name = self.settings.bot_bucket

        self.emit_monitor_event(self.settings, article_id, version, run,
                                self.pretty_name, "end",
                                "Finished ingest digest to endpoint for " + article_id)

        return self.ACTIVITY_SUCCESS

    def approve(self, article_id, status, version, run_type):
        "should we ingest based on some basic attributes"
        approve_status = True
        error_message = ''
        # PoA do not ingest digests
        if status == 'poa':
            approve_status = False
            error_message += '\nNot ingesting digest for PoA article {article_id}'.format(
                article_id=article_id
            )
        return approve_status, error_message

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass
