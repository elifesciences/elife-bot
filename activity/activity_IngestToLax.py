import json
import boto3
from provider import lax_provider
from provider.execution_context import get_session
from activity.objects import Activity

"""
activity_IngestToLax.py activity
"""


class activity_IngestToLax(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_IngestToLax, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "IngestToLax"
        self.pretty_name = "Ingest To Lax"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Prepare data and queue for Lax consumption"
        self.logger = logger

    def do_activity(self, data=None):

        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        run = data["run"]
        session = get_session(self.settings, data, run)
        data["version"] = session.get_value("version")
        data["article_id"] = session.get_value("article_id")
        data["status"] = session.get_value("status")
        data["expanded_folder"] = session.get_value("expanded_folder")
        data["update_date"] = session.get_value("update_date")
        data["run_type"] = session.get_value("run_type")

        queue_connection_settings = {
            "sqs_region": self.settings.sqs_region,
            "aws_access_key_id": self.settings.aws_access_key_id,
            "aws_secret_access_key": self.settings.aws_secret_access_key,
        }

        (
            message,
            queue,
            start_event,
            end_event,
            end_event_details,
            exception,
        ) = self.get_message_queue(data)

        self.emit_monitor_event(*start_event)
        if end_event == "error":
            self.logger.exception(
                "Exception when Preparing Ingest for Lax. Details: %s", exception
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.write_message(queue_connection_settings, queue, message)

        self.emit_monitor_event(*end_event_details)
        return self.ACTIVITY_SUCCESS

    def get_message_queue(self, data=None):
        """
        Given data from an article workflow, return a message to add to the Lax queue,
        and also return values to be sent to the dashboard
        """

        run = data["run"]
        version = data["version"]
        article_id = data["article_id"]
        status = data["status"]

        start_event = None
        try:
            expanded_folder = data["expanded_folder"]
            run_type = data["run_type"]

            start_event = [
                self.settings,
                article_id,
                version,
                run,
                self.pretty_name,
                "start",
                "Starting preparation of article for Lax " + article_id,
            ]

            force = True if ("force" in data and data["force"] == True) else False

            message = lax_provider.prepare_action_message(
                self.settings,
                article_id,
                run,
                expanded_folder,
                version,
                status,
                "ingest",
                force,
                run_type,
            )

            return (
                message,
                self.settings.xml_info_queue,
                start_event,
                "end",
                [
                    self.settings,
                    article_id,
                    version,
                    run,
                    self.pretty_name,
                    "end",
                    "Finished preparation of article for Lax. Ingest sent to Lax"
                    + article_id,
                ],
                None,
            )

        except Exception as exception:
            self.logger.exception("Exception when Preparing Ingest for Lax")
            return (
                None,
                None,
                start_event,
                "error",
                [
                    self.settings,
                    article_id,
                    version,
                    run,
                    self.pretty_name,
                    "error",
                    "Error preparing or sending message to lax"
                    + article_id
                    + " message: "
                    + str(exception),
                ],
                str(exception),
            )

    def write_message(self, connexion_settings, queue, message_data):
        message_body = json.dumps(message_data)
        self.logger.info("Sending message to lax: %s", message_body)
        client = boto3.client(
            "sqs",
            aws_access_key_id=connexion_settings["aws_access_key_id"],
            aws_secret_access_key=connexion_settings["aws_secret_access_key"],
            region_name=connexion_settings["sqs_region"],
        )
        queue_url_response = client.get_queue_url(QueueName=queue)
        queue_url = queue_url_response.get("QueueUrl")
        client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
        )
