import activity
import boto
import json
from boto.sqs.message import Message
from provider.execution_context import get_session


"""
VersionReasonDecider.py activity
"""

class activity_VersionReasonDecider(activity.activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VersionReasonDecider"
        self.version = "1"

        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Decides how workflow proceeds for version reason"
        self.logger = logger

    def do_activity(self, data=None):

        """
        Do the work
        """

        run = data['run']
        session = get_session(self.settings, data, run)
        version = session.get_value('version')
        article_id = session.get_value('article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, "Decide version reason", "start",
                                "Starting decision of version reason decision for " + article_id)

        for key in data.keys():
            session.store_value(key, data[key])

        # uncomment to enable dashboard path
        # if status == 'POA' and version > 1 (and not a silent correction!):
        #   # TODO : alter publication status property in dashboard
        # else:


        self.emit_monitor_event(self.settings, article_id, version, run, "Decide version reason", "end",
                                "Decided version reason for " + article_id)

        return activity.activity.ACTIVITY_SUCCESS
