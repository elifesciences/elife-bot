from activity.objects import Activity

"""
PingWorker activity
"""


class activity_PingWorker(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PingWorker, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "PingWorker"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 10
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Ping a worker to check if running"

    def do_activity(self, data=None):
        """
        PingWorker activity, do the work, in this case
        just return true
        """
        self.result = True
        return True
