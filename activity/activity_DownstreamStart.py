from provider.execution_context import get_session
from activity.objects import Activity


class activity_DownstreamStart(Activity):
    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_DownstreamStart, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

        self.name = "DownstreamStart"
        self.pretty_name = "Downstream Start"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Read downstream deliverable workflow data and store it in the session"
        )
        self.logger = logger

    def do_activity(self, data=None):

        try:
            run = data["run"]
        except (KeyError, TypeError) as exception:
            self.logger.exception(
                "Exception in %s do_activity, misisng run value. Error: %s"
                % (self.name, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            session = get_session(self.settings, data, run)
            for key in ["article_id", "input_file", "recipient", "version", "workflow"]:
                if data.get(key):
                    session.store_value(key, data.get(key))
                    self.logger.info(
                        "Stored %s in session, activity %s" % (key, self.name)
                    )

            return self.ACTIVITY_SUCCESS

        except Exception as exception:
            self.logger.exception(
                "Exception in %s do_activity. Error: %s" % (self.name, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE
