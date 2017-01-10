import activity
import json
from provider.execution_context import Session
import glencoe_check

"""
activity_VerifyLaxResponse.py activity
"""


class ValidationException(RuntimeError):
    pass

class activity_VerifyGlencoe(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VerifyGlencoe"
        self.pretty_name = "Verify Glencoe"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Checks if Glencoe video is available"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        run = data['run']
        session = Session(self.settings)
        article_id = session.get_value(run, 'article_id')
        version = session.get_value(run, 'version')

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting Glencoe video check for " + article_id)

        try:
            glencoe_check.dealwithit(glencoe_check.metadata(article_id))
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Finished Verification. Glencoe is available. Article: " + article_id)
            return True
        except AssertionError as err:
            self.logger.info(err)
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "Glencoe video is not available for article " + article_id + '; message: ' + err)
            print err
            return activity.activity.ACTIVITY_TEMPORARY_FAILURE


