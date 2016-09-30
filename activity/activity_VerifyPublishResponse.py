import activity
import json
from provider.execution_context import Session

"""
activity_VerifyPublishResponse.py activity
"""

class activity_VerifyPublishResponse(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VerifyPublishResponse"
        self.pretty_name = "Verify Publish Response"
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
        version = data['version']
        article_id = data['article_id']

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting verification of Publish response " + article_id)

        try:
            # Verifies authority
            if self.publication_authority(self.settings) == 'Journal':
                if 'requested_action' in data:
                    self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                            "Finish verification of Publish response. Authority: Old Journal. Exiting "
                                            "this workflow " + article_id)

                    return activity.activity.ACTIVITY_EXIT_WORKFLOW # Terminate Workflow gracefully, log

                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                        "Finished verification of Publish response " + article_id)
                return activity.activity.ACTIVITY_SUCCESS
            # Default new site: 2.0
            if 'requested_action' not in data:
                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                        "Finish verification of Publish response. Authority: New site. Exiting this "
                                        "workflow " + article_id)

                return activity.activity.ACTIVITY_EXIT_WORKFLOW
                # Terminate Workflow gracefully, log - this message didn't come from lax. it was from the old
                # pipeline, so Ignore it since the new site is the authority

            if data['result'] == "published":

                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                        " Finished Verification. Lax has responded with result: published."
                                        " Article: " + article_id)

                return activity.activity.ACTIVITY_SUCCESS

            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "Lax has not published article " + article_id +
                                    " result from lax:" + str(data['result']) + '; message from lax: ' + data['message'])
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

            #########

        except Exception as e:
            self.logger.exception("Exception when Verifying Publish Response")
            self.emit_monitor_event(self.settings, article_id, version, run, "Verify Publish Response", "error",
                                    "Error when verifying Publish response" + article_id +
                                    " message:" + str(e.message))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def publication_authority(self, settings):
        return settings.publication_authority