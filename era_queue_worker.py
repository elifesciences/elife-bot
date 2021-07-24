import os
import json
import newrelic.agent
import boto.sqs
from boto.sqs.message import Message
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
        self.conn = None
        self.wait_time_seconds = 10

    def create_log(self):
        # Log
        log_file = "era_queue_worker.log"
        # logFile = None
        self.logger = log.logger(log_file, self.settings.setLevel, self.identity)

    def connect(self):
        "connect to the queue service"
        if not self.conn:
            self.conn = boto.sqs.connect_to_region(
                self.settings.sqs_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )

    def queues(self):
        "get the queues"
        self.connect()
        queue = self.conn.get_queue(self.settings.era_incoming_queue)
        out_queue = self.conn.get_queue(self.settings.workflow_starter_queue)
        return queue, out_queue

    def work(self, flag):
        "read messages from the queue"

        # Simple connect to the queues
        queue, out_queue = self.queues()

        application = newrelic.agent.application()

        # Poll for an activity task indefinitely
        if queue is not None:
            while flag.green():

                self.logger.info("reading message")
                queue_message = queue.read(
                    visibility_timeout=60, wait_time_seconds=self.wait_time_seconds
                )

                if queue_message is None:
                    self.logger.info("no messages available")
                else:
                    with newrelic.agent.BackgroundTask(
                        application,
                        name=self.identity,
                        group="era_queue_worker.py",
                    ):
                        self.logger.info("got message: %s", str(queue_message))

                        message_body = queue_message.get_body()
                        message_dict = json.loads(message_body)

                        # get values from the queue message
                        article_id = message_dict.get("id")
                        input_file = message_dict.get("download")
                        display = message_dict.get("display")

                        # determine if a workflow should be started
                        if self.approve_workflow_start(origin=display):
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
                                "Starting a %s workflow for %s", WORKFLOW_NAME, display
                            )
                            # send workflow initiation message
                            message_object = Message()
                            message_object.set_body(json.dumps(message))
                            out_queue.write(message_object)

                        # cancel incoming message
                        self.logger.info("cancelling message")
                        queue.delete_message(queue_message)
                        self.logger.info("message cancelled")

            self.logger.info("graceful shutdown")

        else:
            self.logger.error("error obtaining queue")

    def approve_workflow_start(self, origin):
        origin_exists = software_heritage.swh_origin_exists(
            url_pattern=self.settings.software_heritage_api_get_origin_pattern,
            origin=origin,
            logger=self.logger,
        )
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
