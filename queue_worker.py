import time
import json
import os
import re
import yaml
import newrelic.agent
import boto3
from provider import process, utils
import log
from S3utility.s3_notification_info import S3NotificationInfo
from S3utility.s3_sqs_message import S3SQSMessage


"""
Amazon SQS worker
"""


class QueueWorker:
    def __init__(self, settings, logger=None, identity="queue_worker"):
        self.identity = identity
        self.settings = settings
        if logger:
            self.logger = logger
        else:
            self.create_log()
        self.client = None
        self.sleep_seconds = 10
        self.input_queue_name = self.settings.S3_monitor_queue
        self.output_queue_name = self.settings.workflow_starter_queue

    def create_log(self):
        # Log
        identity = "%s_%s" % (self.identity, os.getpid())
        log_file = "%s.log" % self.identity
        # logFile = None
        self.logger = log.logger(log_file, self.settings.setLevel, identity)

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
            QueueName=self.input_queue_name
        )
        input_queue_url = input_queue_url_response.get("QueueUrl")
        output_queue_url_response = self.client.get_queue_url(
            QueueName=self.output_queue_name
        )
        output_queue_url = output_queue_url_response.get("QueueUrl")
        return input_queue_url, output_queue_url

    def work(self, flag):
        "read messages from the queue"

        # Simple connect to the queues
        input_queue_url, output_queue_url = self.queues()

        rules = load_rules()
        application = newrelic.agent.application()

        # Poll for messages indefinitely
        if input_queue_url:
            while flag.green():

                self.logger.info("reading message")
                queue_messages = self.client.receive_message(
                    QueueUrl=input_queue_url,
                    MaxNumberOfMessages=1,
                    VisibilityTimeout=30,
                )
                # TODO : check for more-than-once delivery
                # ( Dynamo conditional write? http://tinyurl.com/of3tmop )
                if not queue_messages.get("Messages"):
                    self.logger.info("no messages available")
                else:
                    with newrelic.agent.BackgroundTask(
                        application,
                        name=self.identity,
                        group="%s.py" % self.identity,
                    ):
                        for queue_message in queue_messages.get("Messages"):
                            self.logger.info(
                                "got message id: %s" % queue_message.get("MessageId")
                            )
                            s3_message = S3SQSMessage(queue_message.get("Body"))
                            if s3_message.notification_type == "S3Event":
                                info = S3NotificationInfo.from_S3SQSMessage(s3_message)
                                self.logger.info(
                                    "S3NotificationInfo: %s", info.to_dict()
                                )

                                workflow_name = get_starter_name(rules, info)
                                if workflow_name is None:
                                    self.logger.error(
                                        "Could not handle file %s in bucket %s"
                                        % (info.file_name, info.bucket_name)
                                    )
                                else:
                                    # build message
                                    message = {
                                        "workflow_name": workflow_name,
                                        "workflow_data": info.to_dict(),
                                    }

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
                            else:
                                # TODO : log
                                pass
                time.sleep(self.sleep_seconds)

            self.logger.info("graceful shutdown")

        else:
            self.logger.error("error obtaining queue")


def load_rules():
    # load the rules from the YAML file
    with open("newFileWorkflows.yaml", "r") as open_file:
        return yaml.load(open_file.read(), Loader=yaml.FullLoader)


def get_starter_name(rules, info):
    for rule_name in rules:
        rule = rules[rule_name]
        if re.match(rule["bucket_name_pattern"], info.bucket_name) and re.match(
            rule["file_name_pattern"], info.file_name
        ):
            return rule["starter_name"]


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    queue_worker = QueueWorker(SETTINGS)
    process.monitor_interrupt(lambda flag: queue_worker.work(flag))
