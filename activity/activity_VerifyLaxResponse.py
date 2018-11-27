import json
from provider.execution_context import get_session
from uuid import UUID
from activity.objects import Activity

"""
activity_VerifyLaxResponse.py activity
"""


class ValidationException(RuntimeError):
    pass

class activity_VerifyLaxResponse(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_VerifyLaxResponse, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "VerifyLaxResponse"
        self.pretty_name = "Verify Lax Response"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Verifies data response from Lax in order to decide if we can carry on with workflow"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        ########
        if not self.settings.consider_Lax_elife_2_0:
            return self.ACTIVITY_SUCCESS
        #######

        article_id = data['article_id']
        run = data['run']
        version = data['version']
        force = data['force']
        session = get_session(self.settings, data, run)

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting verification of Lax response " + article_id)

        try:
            if data['result'] == "ingested":
                if force is True:
                    session.store_value('published', True)
                else:
                    session.store_value('published', False)
                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                        " Finished Verification. Lax has responded with result: ingested."
                                        " Article: " + article_id)

                return self.ACTIVITY_SUCCESS

            message = data['message'] if data['message'] is not None else "(empty message)"
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "Lax has not ingested article " + article_id +
                                    " result from lax:" + str(data['result']) + '; message from lax: ' + message)
            return self.ACTIVITY_PERMANENT_FAILURE

        #########

        except Exception as e:
            self.logger.exception("Exception when Verifying Lax Response")
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "Error when verifying lax response" + article_id +
                                    " message:" + str(e.message))
            return self.ACTIVITY_PERMANENT_FAILURE


