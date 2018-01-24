import activity
import base64
import json

from provider.execution_context import get_session

class activity_ReadyToPublish(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ReadyToPublish"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Sends Ready To Publish message to Dashboard"
        self.logger = logger
        self.pretty_name = "Ready To Publish"

    def do_activity(self, data=None):

        run = data['run']
        session = get_session(self.settings, data, run)
        version = session.get_value('version')
        article_id = session.get_value('article_id')

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Sending Ready To Publish message for " + article_id)

        try:

            expanded_folder_name = session.get_value('expanded_folder')
            status = session.get_value('status')
            update_date = session.get_value('update_date')

            article_path = self.preview_path(self.settings.article_path_pattern, article_id, version)

            self.prepare_ready_to_publish_message(article_id, version, run, expanded_folder_name, status,
                                                  update_date, article_path)

        except Exception as e:
            self.logger.exception("Exception when sending Ready To Publish message")
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error",
                                    "Error sending Ready To Publish message for article " + article_id +
                                    " message:" + e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Sending Ready To Publish message. "
                                    "Article: " + article_id)

        return activity.activity.ACTIVITY_SUCCESS

    def preview_path(self, article_path_pattern, article_id, version):
        path = article_path_pattern.format(id=article_id, version=version)
        return path

    def prepare_ready_to_publish_message(self, article_id, version, run, expanded_folder, status, update_date,
                                         article_path):
        workflow_data = {
                'article_id': article_id,
                'version': version,
                'run': run,
                'expanded_folder': expanded_folder,
                'status': status,
                'update_date': update_date
            }

        message = {
            'workflow_name': 'PostPerfectPublication',
            'workflow_data': workflow_data
        }

        encoded_message = base64.encodestring(json.dumps(message))

        self.set_monitor_property(self.settings, article_id, 'path',
                                  article_path, 'text', version=version)

        # store message in dashboard for later
        self.set_monitor_property(self.settings, article_id, "_publication-data",
                                  encoded_message, "text", version=version)
        self.set_monitor_property(self.settings, article_id, "publication-status",
                                  "ready to publish", "text", version=version)