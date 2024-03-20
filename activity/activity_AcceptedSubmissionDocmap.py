import json
from provider.execution_context import get_session
from provider import cleaner
from activity.objects import AcceptedBaseActivity


class activity_AcceptedSubmissionDocmap(AcceptedBaseActivity):
    "AcceptedSubmissionDocmap activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionDocmap, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionDocmap"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 10
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 10
        self.description = (
            "Get a docmap string to use in the accepted submission ingestion."
        )

        # Track the success of some steps
        self.statuses = {"docmap_string": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        # if the article is not PRC, return True
        prc_status = session.get_value("prc_status")
        if not prc_status:
            self.logger.info(
                "%s, %s prc_status session value is %s, activity returning True"
                % (self.name, input_filename, prc_status)
            )
            return True

        # get docmap as a string
        try:
            docmap_string = cleaner.get_docmap_string_with_retry(
                self.settings, article_id, self.name, self.logger
            )
            self.statuses["docmap_string"] = True
            # save the docmap_string to the session
            session.store_value("docmap_string", docmap_string)
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting a docmap for article_id %s: %s"
                % (self.name, article_id, str(exception))
            )

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True
