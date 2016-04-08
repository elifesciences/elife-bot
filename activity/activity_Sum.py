import json

import activity

"""
Sum activity
"""

class activity_Sum(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "Sum"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 10
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Sum of numbers, a testing activity."

    def do_activity(self, data=None):
        """
        Sum activity, do the work, in this case
        sum the data and return true
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        self.result = sum(data["data"])
        return True
