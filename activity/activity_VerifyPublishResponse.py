import json
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
        self.description = "Verifies data response from Lax in order to decide if we can carry on with workflow"
        self.logger = logger

    def do_activity(self, data=None):
        (start_msg, end_msg, set_status, result) = self.get_events(data, self.publication_authority(self.settings))
        self.emit_monitor_event(*start_msg)
        self.emit_monitor_event(*end_msg)
        if set_status is not None:
            self.set_monitor_property(*set_status, version=data['version'])
        return result

    def get_events(self, data, pub_authority):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        article_id = data['article_id']

        try:
            run = data['run']
            version = data['version']
            return self.publication_verification_results(data, 'journal', 'journal',
                                                         success=data['result'] == "published")

        except Exception:
            self.logger.exception("Exception when Verifying Publish Response")
            raise

    def publication_authority(self, settings):
        return settings.publication_authority

    def publication_verification_results(self, data, pub_authority, checking_result_from, success):

        if pub_authority == 'journal' and checking_result_from == 'journal' and success:

            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + data['article_id']]

            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": journal", "end",
                         " Finished Verification. Lax has responded with result: published."
                         " Article: " + data['article_id']]

            set_status_property = [self.settings, data['article_id'], "publication-status", "published", "text"]
            success = self.ACTIVITY_SUCCESS
            return start_event, end_event, set_status_property, success

        elif pub_authority == 'journal' and checking_result_from == 'journal' and success is False:

            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + data['article_id']]

            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": journal", "error",
                         " Lax has not published article " + data['article_id'] +
                         " result from lax:" + str(data['result']) + '; message from lax: ' +
                         data['message'] if ("message" in data) and (data['message'] is not None) else "(empty message)"]

            set_status_property = [self.settings, data['article_id'], "publication-status", "publication issues",
                                "text"]
            success = self.ACTIVITY_PERMANENT_FAILURE
            return start_event, end_event, set_status_property, success

        else:
            raise RuntimeError("The publication result isn't a valid one.")
