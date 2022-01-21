import json
from provider.execution_context import get_session
from provider.utils import base64_encode_string
from provider.token import starter_message
from activity.objects import Activity


class activity_ReadyToPublish(Activity):
    def __init__(
        self, settings, logger, conn=None, token=None, activity_task=None, client=None
    ):
        super(activity_ReadyToPublish, self).__init__(
            settings, logger, conn, token, activity_task, client=client
        )

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

        run = data["run"]
        session = get_session(self.settings, data, run)
        version = session.get_value("version")
        article_id = session.get_value("article_id")

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            self.pretty_name,
            "start",
            "Sending Ready To Publish message for " + article_id,
        )

        try:

            expanded_folder_name = session.get_value("expanded_folder")
            status = session.get_value("status")
            update_date = session.get_value("update_date")
            run_type = session.get_value("run_type")

            article_path = preview_path(
                self.settings.article_path_pattern, article_id, version
            )

            publication_data_message = starter_message(
                article_id=article_id,
                version=version,
                run=run,
                expanded_folder=expanded_folder_name,
                status=status,
                update_date=update_date,
                run_type=run_type,
                workflow_name="PostPerfectPublication",
            )

            self.prepare_ready_to_publish_message(
                article_id, version, article_path, publication_data_message
            )

        except Exception as exception:
            self.logger.exception("Exception when sending Ready To Publish message")
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "error",
                "Error sending Ready To Publish message for article "
                + article_id
                + " message:"
                + str(exception),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            self.pretty_name,
            "end",
            "Sending Ready To Publish message. " + "Article: " + article_id,
        )

        return self.ACTIVITY_SUCCESS

    def prepare_ready_to_publish_message(
        self, article_id, version, article_path, publication_data_message
    ):

        encoded_message = base64_encode_string(json.dumps(publication_data_message))

        self.set_monitor_property(
            self.settings, article_id, "path", article_path, "text", version=version
        )

        # store message in dashboard for later
        self.set_monitor_property(
            self.settings,
            article_id,
            "_publication-data",
            encoded_message,
            "text",
            version=version,
        )
        self.set_monitor_property(
            self.settings,
            article_id,
            "publication-status",
            "ready to publish",
            "text",
            version=version,
        )


def preview_path(article_path_pattern, article_id, version):
    return article_path_pattern.format(id=article_id, version=version)
