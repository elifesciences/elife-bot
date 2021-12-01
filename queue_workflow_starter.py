"""
Process SQS message from queue and start required workflow
"""
import os
import uuid
import json
import importlib
import log
import boto.sqs
import newrelic.agent
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
    queue = get_queue(settings)

    while flag.green():
        messages = queue.get_messages(1, visibility_timeout=60, wait_time_seconds=20)
        if messages:
            logger.info(str(len(messages)) + " message received")
            logger.info("message contents: %s", messages[0].get_body())
            process_message(settings, logger, messages[0])
        else:
            logger.debug("No messages received")

    logger.info("graceful shutdown")


def get_queue(settings):
    conn = boto.sqs.connect_to_region(
        settings.sqs_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    queue = conn.get_queue(settings.workflow_starter_queue)
    return queue


def process_message(settings, logger, message):
    try:
        message_payload = json.loads(str(bytes_decode(message.get_body())))
        name = message_payload.get("workflow_name")
        data = message_payload.get("workflow_data")
        start_workflow(settings, name, data)
    except Exception:
        logger.exception("Exception while processing %s", message.get_body())
    message.delete()


@newrelic.agent.background_task(group="queue_workflow_starter.py")
def start_workflow(settings, workflow_name, workflow_data):
    data_processor = workflow_data_processors.get(workflow_name)
    workflow_name = "starter_" + workflow_name
    if data_processor is not None:
        workflow_data = data_processor(workflow_data)
    module_name = "starter." + workflow_name
    importlib.import_module(module_name)
    full_path = "starter." + workflow_name + "." + workflow_name + "()"
    starter_object = eval(full_path)
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


workflow_data_processors = {
    "IngestArticleZip": process_data_ingestarticlezip,
    "SilentCorrectionsIngest": process_data_ingestarticlezip,
    "PostPerfectPublication": process_data_postperfectpublication,
    "PubmedArticleDeposit": process_data_pubmedarticledeposit,
    "IngestDigest": process_data_ingestdigest,
    "IngestDecisionLetter": process_data_ingestdecisionletter,
    "IngestAcceptedSubmission": process_data_ingestacceptedsubmission,
}


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    process.monitor_interrupt(lambda flag: main(SETTINGS, flag))
