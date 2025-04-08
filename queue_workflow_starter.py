"""
Process SQS message from queue and start required workflow
"""
import os
import uuid
import json
import importlib
import log
from S3utility.s3_notification_info import S3NotificationInfo
from provider import process, utils
from provider.utils import bytes_decode

# this is not an unused import, it is used dynamically
import starter

"""
Example message:

{
    "workflow_name": "event"
    "workflow_data": {
        "article_version_id": 05224.1
    }
}
"""


def main(settings, flag):
    log_file = "queue_workflow_starter.log"
    identity = "queue_workflow_starter_%s" % os.getpid()
    logger = log.logger(log_file, settings.setLevel, identity=identity)
    # Simple connect
    client = connect(settings)
    # get the queue url
    queue_url_response = client.get_queue_url(QueueName=settings.workflow_starter_queue)
    queue_url = queue_url_response.get("QueueUrl")
    while flag.green():
        messages = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            VisibilityTimeout=60,
            WaitTimeSeconds=20,
        )
        if messages.get("Messages"):
            logger.info(str(len(messages.get("Messages"))) + " message received")
            message = messages.get("Messages")[0]
            logger.info("message contents: %s", message.get("Body"))
            process_message(settings, logger, message)
            client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message.get("ReceiptHandle"),
            )
        else:
            logger.debug("No messages received")

    logger.info("graceful shutdown")


def connect(settings):
    "connect to the queue service"
    return settings.aws_conn('sqs', {
        'aws_access_key_id': settings.aws_access_key_id,
        'aws_secret_access_key': settings.aws_secret_access_key,
        'region_name': settings.sqs_region,
    })

def process_message(settings, logger, message):
    message_payload = {}
    try:
        message_payload = json.loads(str(bytes_decode(message.get("Body"))))
    except json.decoder.JSONDecodeError:
        # decode messages from the dashboard queue
        decoded_body = utils.base64_decode_string(message.get("Body"))
        message_payload = json.loads(decoded_body)

    try:
        name = message_payload.get("workflow_name")
        data = message_payload.get("workflow_data")
        execution_start_to_close_timeout = message_payload.get("execution_start_to_close_timeout")
        start_workflow(settings, name, data, execution_start_to_close_timeout)
    except Exception:
        logger.exception("Exception while processing %s", message.get("Body"))


def start_workflow(settings, workflow_name, workflow_data, execution_start_to_close_timeout):
    data_processor = workflow_data_processors.get(workflow_name)
    workflow_name = "starter_" + workflow_name
    if data_processor is not None:
        workflow_data = data_processor(workflow_data)
    module_name = "starter." + workflow_name
    importlib.import_module(module_name)
    full_path = "starter." + workflow_name + "." + workflow_name + "()"
    starter_object = eval(full_path)
    if execution_start_to_close_timeout:
        starter_object.execution_start_to_close_timeout = execution_start_to_close_timeout
    starter_object.start(settings=settings, **workflow_data)


def process_data_ingestarticlezip(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_s3_notification_default(workflow_data):
    """definition for default data in response to an S3 notification"""
    data = {
        "info": S3NotificationInfo.from_dict(workflow_data),
        "run": str(uuid.uuid4()),
    }
    return data


def process_data_postperfectpublication(workflow_data):
    data = {"info": workflow_data}
    return data


def process_data_pubmedarticledeposit(workflow_data):
    data = {}
    return data


def process_data_ingestdigest(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_ingestdecisionletter(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_ingestacceptedsubmission(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_silentingestmeca(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_finish_preprint_publication(workflow_data):
    return workflow_data


workflow_data_processors = {
    "IngestArticleZip": process_data_ingestarticlezip,
    "SilentCorrectionsIngest": process_data_ingestarticlezip,
    "PostPerfectPublication": process_data_postperfectpublication,
    "PubmedArticleDeposit": process_data_pubmedarticledeposit,
    "IngestDigest": process_data_ingestdigest,
    "IngestDecisionLetter": process_data_ingestdecisionletter,
    "IngestAcceptedSubmission": process_data_ingestacceptedsubmission,
    "SilentIngestMeca": process_data_silentingestmeca,
    "FinishPreprintPublication": process_finish_preprint_publication,
}


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    process.monitor_interrupt(lambda flag: main(SETTINGS, flag))
