import activity
import json
from provider.execution_context import Session

"""
activity_VerifyLaxResponse.py activity
"""


class activity_VerifyLaxResponse(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VerifyLaxResponse"
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

        run = data['run']
        session = Session(self.settings)
        version = session.get_value(run, 'version')
        article_id = session.get_value(run, 'article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, "Verify Lax Response", "start",
                                "Starting verification of Lax response " + article_id)

        try:
            if data['result'] == "ingested":

                self.emit_monitor_event(self.settings, article_id, version, run, "Verify Lax Response", "end",
                                        " Finished Verification. Lax has responded with result: ingested."
                                        " Article: " + article_id)

                return True

            self.emit_monitor_event(self.settings, article_id, version, run, "Ingest To Lax", "error",
                                    "Lax has not ingested article " + article_id +
                                    " result from lax:" + str(data['result']) + '; message from lax: ' + data['message'])
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

            #########

        except Exception as e:
            self.logger.exception("Exception when Verifying Lax Response")
            self.emit_monitor_event(self.settings, article_id, version, run, "Verify Lax Response", "error",
                                    "Error when verifying lax response" + article_id +
                                    " message:" + str(e.message))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE
