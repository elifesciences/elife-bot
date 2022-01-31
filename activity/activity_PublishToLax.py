import json
from provider.execution_context import get_session
import boto.sqs
from boto.sqs.message import RawMessage
import provider.lax_provider as lax_provider
from provider.utils import base64_decode_string
from activity.objects import Activity

"""
activity_PublishToLax.py activity
"""


class activity_PublishToLax(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PublishToLax, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "PublishToLax"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Prepare data and queue for Lax consumption for publishing"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        article_id = data["article_id"]
        version = data["version"]
        run = data["run"]

        workflow_data = self.get_workflow_data(data)

        status = workflow_data["status"]
        expanded_folder = workflow_data["expanded_folder"]
        run_type = workflow_data.get("run_type")

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            "Publish To Lax",
            "start",
            "Starting preparation of article for Lax " + article_id,
        )

        try:
            force = True if ("force" in data and data["force"] == True) else False
            message = lax_provider.prepare_action_message(
                self.settings,
                article_id,
                run,
                expanded_folder,
                version,
                status,
                "publish",
                force,
                run_type,
            )
            message_body = json.dumps(message)
            self.logger.info("Sending message to lax: %s", message_body)
            sqs_conn = boto.sqs.connect_to_region(
                self.settings.sqs_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )
            out_queue = sqs_conn.get_queue(self.settings.xml_info_queue)
            m = RawMessage()
            m.set_body(message_body)
            out_queue.write(m)

            #########

        except Exception as exception:
            self.logger.exception("Exception when Preparing Publish action for Lax")
            self.emit_monitor_event(
                self.settings,
                article_id,
                version,
                run,
                "Publish To Lax",
                "error",
                "Error preparing or sending message to lax"
                + article_id
                + " message:"
                + str(exception),
            )
            return False

        self.emit_monitor_event(
            self.settings,
            article_id,
            version,
            run,
            "Publish To Lax",
            "end",
            "Finished preparation of article for Lax " + article_id,
        )
        return True

    def get_workflow_data(self, data):
        if "publication_data" in data:
            publication_data = json.loads(
                base64_decode_string(data["publication_data"])
            )
            workflow_data = publication_data["workflow_data"]
            return workflow_data

        return data
