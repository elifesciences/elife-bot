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
        (start_msg, end_msg, result) = self.get_events(data, self.publication_authority(self.settings))
        self.emit_monitor_event(*start_msg)
        self.emit_monitor_event(*end_msg)
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
                    start_event = [self.settings, article_id, version, run, self.pretty_name + ": Journal", "start",
                                   "Starting verification of Publish response " + article_id]

                    # Before terminating Workflow gracefully, emit the result of publication to lax on the dashboard
                    # Terminate Workflow gracefully, log
                    if data['result'] == "published":
                        return [start_event,
                                [self.settings, article_id, version, run, self.pretty_name + ": Journal", "end",
                                 " Finished Verification. Lax has responded with result: published."
                                 " Authority: elife-website. Exiting."
                                 " Article: " + article_id],
                                activity.activity.ACTIVITY_SUCCESS]
                    else:
                        return [start_event,
                                [self.settings, article_id, version, run, self.pretty_name + ": Journal", "error",
                                 " Lax has not published article " + article_id +
                                 " We will exit this workflow as the publication authority is elife-website."
                                 " result from lax:" + str(data['result']) + '; message from lax: ' +
                                 data['message'] if ("message" in data) and (data['message'] is not None) else "(empty message)"],
                                activity.activity.ACTIVITY_PERMANENT_FAILURE]

                start_event = [self.settings, article_id, version, run, self.pretty_name + ": elife-website", "start",
                               "Starting verification of Publish response " + article_id]
                return [start_event, [self.settings, article_id, version, run,
                                      self.pretty_name + ": elife-website",
                                      "end",
                                      "Finished verification of Publish response " + article_id],
                        activity.activity.ACTIVITY_SUCCESS]

            # Default new site: 2.0
            if 'requested_action' not in data:
                # Terminate Workflow gracefully, log - this message didn't come from lax. it was from the old
                # pipeline, so Ignore it since the new site is the authority
                start_event = [self.settings, article_id, version, run, self.pretty_name + ": elife-website", "start",
                               "Starting verification of Publish response " + article_id]
                return [start_event,
                       [self.settings, article_id, version, run, self.pretty_name + ": elife-website", "end",
                        "Finish verification of Publish response. Authority: Journal. Exiting this "
                        "workflow " + article_id],
                        activity.activity.ACTIVITY_EXIT_WORKFLOW]

            if data['result'] == "published":
                start_event = [self.settings, article_id, version, run, self.pretty_name + ": Journal", "start",
                               "Starting verification of Publish response " + article_id]
                return [start_event,
                        [self.settings, article_id, version, run, self.pretty_name + ": Journal", "end",
                         " Finished Verification. Lax has responded with result: published."
                         " Article: " + article_id],
                        activity.activity.ACTIVITY_SUCCESS]

            start_event = [self.settings, article_id, version, run, self.pretty_name + ": Journal", "start",
                           "Starting verification of Publish response " + article_id]
            return [start_event,
                    [self.settings, article_id, version, run, self.pretty_name + ": Journal", "error",
                     " Lax has not published article " + article_id +
                     " result from lax:" + str(data['result']) + '; message from lax: ' +
                     data['message'] if ("message" in data) and (data['message'] is not None) else "(empty message)"],
                    activity.activity.ACTIVITY_PERMANENT_FAILURE]

            #########

        except KeyError as e:
            self.logger.exception("Exception when Verifying Publish Response")
            return [start_event,
                    [self.settings, article_id, None, None, "Verify Publish Response", "error",
                     "Error when verifying Publish response" + article_id +
                     " message:" + str(e.message)]
                    , activity.activity.ACTIVITY_PERMANENT_FAILURE]

        except Exception as e:
            self.logger.exception("Exception when Verifying Publish Response")
            return [start_event,
                    [self.settings, article_id, version, run, "Verify Publish Response", "error",
                     "Error when verifying Publish response" + article_id +
                     " message:" + str(e.message)],
                    activity.activity.ACTIVITY_PERMANENT_FAILURE]

    def publication_authority(self, settings):
        return settings.publication_authority
