import json
from provider.lax_provider import message_from_lax
from activity.objects import Activity

"""
activity_VerifyPublishResponse.py activity
"""


class activity_VerifyPublishResponse(Activity):

    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_VerifyPublishResponse, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "VerifyPublishResponse"
        self.pretty_name = "Verify Publish Response"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Verifies data response from Lax in order to decide if we can " +
                            "carry on with workflow")

    def do_activity(self, data=None):
        start_msg, end_msg, set_status, result = self.get_events(data)
        self.emit_monitor_event(*start_msg)
        self.emit_monitor_event(*end_msg)
        if set_status is not None:
            self.set_monitor_property(*set_status, version=data['version'])
        return result

    def get_events(self, data):
        """
        Given the data for this activity from Lax and the activity starter,
        return start and end messages to send to the dashboard queue,
        also return the status return from Lax, and the return value for this workflow activity
        """
        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            return self.publication_verification_results(
                data, success=data['result'] == "published")

        except Exception:
            self.logger.exception("Exception when Verifying Publish Response")
            raise

    def publication_verification_results(self, data, success):

        article_id = data['article_id']
        version = data['version']
        run = data['run']

        if success:

            start_event = [self.settings, article_id, version, run,
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + article_id]

            end_event = [self.settings, article_id, version, run,
                         self.pretty_name + ": journal", "end",
                         " Finished Verification. Lax has responded with result: published."
                         " Article: " + article_id]

            set_status_property = [
                self.settings, article_id, "publication-status", "published", "text"]
            success = self.ACTIVITY_SUCCESS
            return start_event, end_event, set_status_property, success

        elif success is False:

            start_event = [self.settings, article_id, version, run,
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + article_id]

            end_event = [self.settings, article_id, version, run,
                         self.pretty_name + ": journal", "error",
                         " Lax has not published article " + article_id +
                         " result from lax:" + str(data['result']) + '; message from lax: ' +
                         message_from_lax(data)]

            set_status_property = [
                self.settings, article_id, "publication-status",
                "publication issues", "text"]
            success = self.ACTIVITY_PERMANENT_FAILURE
            return start_event, end_event, set_status_property, success

        else:
            raise RuntimeError("The publication result isn't a valid one.")
