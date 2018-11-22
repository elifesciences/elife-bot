from provider.execution_context import get_session
from .activity import Activity

"""
AcceptVersionReason.py activity
"""


class activity_AcceptVersionReason(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_AcceptVersionReason, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "AcceptVersionReason"
        self.pretty_name = "Accept version reason"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Accept version reason and date parameters from dashboard"
        self.logger = logger

    def do_activity(self, data=None):

        try:

            run = data['run']
            session = get_session(self.settings, data, run)
            version = session.get_value('version')
            article_id = session.get_value('article_id')

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start",
                                    "Starting accept version reason for article " + article_id)

            # these are new values introduced with the input data to this workflow
            # calling set on the session ensures they'll be there for all follow-on workflows
            # values also set as properties and will be sent to Exeter and other listeners

            version_reason = data.get('version_reason')
            if version_reason is not None:
                session.store_value('version_reason', version_reason)
                self.set_monitor_property(self.settings, article_id, 'version_reason', version_reason,
                                          "text", version=version)
            scheduled_publication_date = data.get('scheduled_publication_date')
            if scheduled_publication_date is not None:
                session.store_value('scheduled_publication_date', scheduled_publication_date)
                self.set_monitor_property(self.settings, article_id, 'scheduled_publication_date',
                                          scheduled_publication_date,  "text", version=version)

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end",
                                    "Accepted version reason for article " + article_id)

        except Exception as e:
            self.logger.exception(str(e))
            return self.ACTIVITY_PERMANENT_FAILURE

        return self.ACTIVITY_SUCCESS
