import boto3
from provider import utils
import starter.starter_helper as helper
from starter.objects import Starter
from S3utility.s3_notification_info import S3NotificationInfo
from S3utility.s3_sqs_message import S3SQSMessage

"""
Cron job to check for new article S3 POA and start workflows
"""

# Note: boto accepts a number between 1 and 10
MAX_MESSAGE_COUNT = 10


class cron_NewS3POA(Starter):
    def __init__(self, settings=None, logger=None):
        super(cron_NewS3POA, self).__init__(settings, logger, "cron_NewS3POA")

    def start(self, settings):
        """method for backwards compatibility"""
        self.settings = settings
        self.instantiate_logger()
        self.start_workflow()

    def start_workflow(self):

        ping_marker_id = "cron_NewS3POA"

        # Start a ping workflow as a marker
        helper.start_ping_marker(ping_marker_id, self.settings, self.logger)

        # Get data from SQS queue
        sqs_client = sqs_connect(self.settings)
        process_queue(sqs_client, self.settings, self.logger)


def sqs_connect(settings):
    """connect to the queue service"""
    return boto3.client(
        "sqs",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.sqs_region,
    )


def process_queue(sqs_client, settings, logger):
    """reach each message from the queue, start a workflow, then delete the message"""
    message_count = 0
    queue_url_response = sqs_client.get_queue_url(QueueName=settings.poa_incoming_queue)
    queue_url = queue_url_response.get("QueueUrl")
    while True:
        try:
            messages = get_queue_messages(
                sqs_client, queue_url, MAX_MESSAGE_COUNT, logger
            )
        except:
            logger.exception(
                "Breaking process queue read loop, failed to get messages from queue"
            )
            break

        # check if any messages to process
        if not messages.get("Messages"):
            logger.info("no messages available")
            break
        else:
            logger.info("Processing %s messages" % len(messages))

        # process each message, deleting each message when done
        for message in messages.get("Messages"):
            # increment count
            message_count += 1
            logger.info("Processing message number %s", message_count)

            s3_message = S3SQSMessage(message.get("Body"))
            # check message type
            if s3_message.notification_type != "S3Event":
                logger.info(
                    "Message not processed, deleting it from queue: %s"
                    % s3_message.payload
                )
                sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message.get("ReceiptHandle"),
                )
                continue

            # start a workflow
            try:
                logger.info("Starting workflow for message: %s" % s3_message)
                start_package_poa_workflow(s3_message, settings, logger)
            except:
                logger.exception(
                    "Exception processing message, deleting it from queue: %s"
                    % s3_message.payload
                )
            finally:
                sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=message.get("ReceiptHandle"),
                )


def get_queue_messages(sqs_client, queue_url, num_messages, logger):
    try:
        return sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=num_messages,
        )
    except:
        logger.exception("Exception in getting messages from SQS queue")
        raise


def start_package_poa_workflow(sqs_message, settings, logger):
    """
    Start a PackagePOA workflow for the file in the SQS message
    """
    info = S3NotificationInfo.from_S3SQSMessage(sqs_message)
    logger.info("S3NotificationInfo: %s", info.to_dict())
    document = info.file_name
    starter_name = "starter_PackagePOA"
    try:
        helper.import_starter_module(starter_name, logger)
        starter_object = helper.get_starter_module(starter_name, logger)
        starter_object.start(settings=settings, document=document)
        logger.info("Started %s workflow for document %s" % (starter_name, document))
    except:
        logger.exception(
            "Error: starting %s for document %s" % (starter_name, document)
        )
        raise


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    STARTER = cron_NewS3POA()

    STARTER.start(settings=SETTINGS)
