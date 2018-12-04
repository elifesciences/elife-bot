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

            # Verifies authority
            if pub_authority == 'elife-website':

                if 'requested_action' in data:
                    # Publication authority is the old site but this call is from new lax.
                    # Before terminating Workflow gracefully, emit the result of publication to lax on the dashboard
                    # Terminate Workflow gracefully, log
                    return self.publication_verification_results(data, pub_authority, 'journal',
                                                                 success=data['result'] == "published")

                return self.publication_verification_results(data, pub_authority, pub_authority, success=True)

            # Default new site: 2.0
            if 'requested_action' not in data:
                # Terminate Workflow gracefully, log - this message didn't come from lax. it was from the old
                # pipeline, so Ignore it since the new site is the authority
                return self.publication_verification_results(data, 'journal', 'elife-website', success=True)

            return self.publication_verification_results(data, 'journal', 'journal',
                                                         success=data['result'] == "published")

            #########

        except Exception:
            self.logger.exception("Exception when Verifying Publish Response")
            raise

    def publication_authority(self, settings):
        return settings.publication_authority

    def publication_verification_results(self, data, pub_authority, checking_result_from, success):

        if pub_authority == 'elife-website' and checking_result_from == 'elife-website' and success:
            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": elife-website", "start",
                           "Starting verification of Publish response " + data['article_id']]

            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": elife-website",
                         "end", "Finished verification of Publish response " + data['article_id']]

            set_status_event = None
            success = self.ACTIVITY_SUCCESS
            return start_event, end_event, set_status_event, success

        elif pub_authority == 'elife-website' and checking_result_from == 'journal' and success:
            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + data['article_id']]

            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": journal", "end",
                         " Finished Verification. Lax has responded with result: published."
                         " Authority: elife-website. Exiting."
                         " Article: " + data['article_id']]

            set_status_property = [self.settings, data['article_id'], "publication-status", "published", "text"]
            success = self.ACTIVITY_EXIT_WORKFLOW
            return start_event, end_event, set_status_property, success

        elif pub_authority == 'elife-website' and checking_result_from == 'journal' and success is False:

            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": journal", "start",
                           "Starting verification of Publish response " + data['article_id']]
            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": journal", "error",
                         " Lax has not published article " + data['article_id'] +
                         " We will exit this workflow as the publication authority is elife-website."
                         " result from lax:" + str(data['result']) + '; message from lax: ' +
                         data['message'] if ("message" in data) and (data['message'] is not None) else "(empty message)"]

            set_status_property = [self.settings, data['article_id'], "publication-status", "publication issues",
                                "text"]
            success = self.ACTIVITY_PERMANENT_FAILURE
            return start_event, end_event, set_status_property, success

        elif pub_authority == 'journal' and checking_result_from == 'journal' and success:

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

        elif pub_authority == 'journal' and checking_result_from == 'elife-website' and success:

            start_event = [self.settings, data['article_id'], data['version'], data['run'],
                           self.pretty_name + ": elife-website", "start",
                           "Starting verification of Publish response " + data['article_id']]
            end_event = [self.settings, data['article_id'], data['version'], data['run'],
                         self.pretty_name + ": elife-website", "end",
                         "Finish verification of Publish response. Authority: journal. Exiting this "
                         "workflow " + data['article_id']]

            set_status_property = None
            success = self.ACTIVITY_EXIT_WORKFLOW
            return start_event, end_event, set_status_property, success

        else:
            raise RuntimeError("The publication result isn't a valid one.")
