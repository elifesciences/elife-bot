import activity
from provider.execution_context import Session


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
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, "Decide version reason", "start",
                                "Starting decision of version reason workflow for " + article_id)

        workflow_data = data.copy()

        workflow_data['article_id'] = article_id
        workflow_data['version'] = version
        workflow_data['filename_last_element'] = session.get_value['filename_last_element']

        message = {
            'workflow_name': 'ApproveArticlePublication',
            'workflow_data': workflow_data
        }

        # if status == 'POA' and version > 1:
        #    send_to_dashboard()
        # else:

        # start workflow

        return activity.activity.ACTIVITY_SUCCESS
