import os
import json
import newrelic.agent
import boto3
import log
from provider import process, software_heritage, utils


WORKFLOW_NAME = "SoftwareHeritageDeposit"


class EraQueueWorker:
    """
    Worker process to read messages from an SQS queue containing
    ERA article messages, and decide whether workflow executions
    should be started, for example to send the files to the
    Software Heritage repository
    """

    def __init__(self, settings, logger=None):
        self.settings = settings
        self.identity = "era_queue_worker_%s" % os.getpid()
        if logger:
            self.logger = logger
        else:
            self.create_log()
        self.client = None
        self.wait_time_seconds = 10

    def create_log(self):
        # Log
        log_file = "era_queue_worker.log"
        # logFile = None
        self.logger = log.logger(log_file, self.settings.setLevel, self.identity)

    def connect(self):
        "connect to the queue service"
        if not self.client:
            self.client = boto3.client(
                "sqs",
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.sqs_region,
            )

    def queues(self):
        "get the queues"
        self.connect()
        input_queue_url_response = self.client.get_queue_url(
            QueueName=self.settings.era_incoming_queue
        )
        input_queue_url = input_queue_url_response.get("QueueUrl")
        output_queue_url_response = self.client.get_queue_url(
            QueueName=self.settings.workflow_starter_queue
        )
        output_queue_url = output_queue_url_response.get("QueueUrl")
        return input_queue_url, output_queue_url

    def work(self, flag):
        "read messages from the queue"

        # Simple connect to the queues
        input_queue_url, output_queue_url = self.queues()

        application = newrelic.agent.application()

        # Poll for an activity task indefinitely
        if input_queue_url:
            while flag.green():

                self.logger.info("reading message")
                queue_messages = self.client.receive_message(
                    QueueUrl=input_queue_url,
                    MaxNumberOfMessages=1,
                    VisibilityTimeout=60,
                    WaitTimeSeconds=self.wait_time_seconds,
                )

                if not queue_messages.get("Messages"):
                    self.logger.info("no messages available")
                else:
                    with newrelic.agent.BackgroundTask(
                        application,
                        name=self.identity,
                        group="era_queue_worker.py",
                    ):
                        for queue_message in queue_messages.get("Messages"):
                            self.logger.info(
                                "got message id: %s" % queue_message.get("MessageId")
                            )

                            message_body = queue_message.get("Body")
                            try:
                                message_dict = json.loads(message_body)
                            except json.decoder.JSONDecodeError as exception:
                                self.logger.exception(
                                    "Exception loading message body as JSON: %s: %s"
                                    % (message_body, str(exception))
                                )
                                message_dict = {}

                            # get values from the queue message
                            article_id = message_dict.get("id")
                            input_file = message_dict.get("download")
                            display = message_dict.get("display")

                            origin = software_heritage.display_to_origin(display)
                            self.logger.info(
                                'display value "%s" turned into origin value "%s"',
                                display,
                                origin,
                            )

                            # determine if a workflow should be started
                            if origin:
                                if self.approve_workflow_start(origin=origin):
                                    run = None
                                    info = {
                                        "article_id": article_id,
                                        "version": "1",
                                        "workflow": "software_heritage",
                                        "recipient": "software_heritage",
                                        "input_file": input_file,
                                        "data": {
                                            "display": display,
                                        },
                                    }
                                    workflow_data = {"run": run, "info": info}

                                    # build message
                                    message = {
                                        "workflow_name": WORKFLOW_NAME,
                                        "workflow_data": workflow_data,
                                    }
                                    self.logger.info(
                                        "Starting a %s workflow for %s",
                                        WORKFLOW_NAME,
                                        display,
                                    )
                                    # send workflow initiation message
                                    self.client.send_message(
                                        QueueUrl=output_queue_url,
                                        MessageBody=json.dumps(message),
                                    )

                                # cancel incoming message
                                self.logger.info("cancelling message")
                                self.client.delete_message(
                                    QueueUrl=input_queue_url,
                                    ReceiptHandle=queue_message.get("ReceiptHandle"),
                                )
                                self.logger.info("message cancelled")

            self.logger.info("graceful shutdown")

        else:
            self.logger.error("error obtaining queue")

    def approve_workflow_start(self, origin):
        try:
            origin_exists = software_heritage.swh_origin_exists(
                url_pattern=self.settings.software_heritage_api_get_origin_pattern,
                origin=origin,
                logger=self.logger,
            )
        except:
            self.logger.exception(
                "Exception when checking swh_origin_exists for origin %s" % origin
            )
            return False
        if origin_exists is None:
            self.logger.info("Could not determine the status of the origin %s", origin)
            return False
        if origin_exists is True:
            self.logger.info("Origin %s already exists at Software Heritage", origin)
            return False
        if origin_exists is False:
            self.logger.info(
                "Origin %s does not exist yet at Software Heritage", origin
            )
        return True


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    QUEUE_WORKER = EraQueueWorker(SETTINGS)
    process.monitor_interrupt(lambda flag: QUEUE_WORKER.work(flag))
