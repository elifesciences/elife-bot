"""
Process SQS message from queue and start required workflow
"""
import os
import uuid
import json
import importlib
from optparse import OptionParser
import log
import boto.sqs
import newrelic.agent
from S3utility.s3_notification_info import S3NotificationInfo
from provider import process
from provider.utils import unicode_decode
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
        messages = queue.get_messages(1, visibility_timeout=60,
                                      wait_time_seconds=20)
        if messages:
            logger.info(str(len(messages)) + " message received")
            logger.info('message contents: %s', messages[0].get_body())
            process_message(settings, logger, messages[0])
        else:
            logger.debug("No messages received")

    logger.info("graceful shutdown")


def get_queue(settings):
    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.workflow_starter_queue)
    return queue


def process_message(settings, logger, message):
    try:
        message_payload = json.loads(str(unicode_decode(message.get_body())))
        name = message_payload.get('workflow_name')
        data = message_payload.get('workflow_data')
        start_workflow(settings, name, data)
    except Exception:
        logger.exception("Exception while processing %s", message.get_body())
    message.delete()


@newrelic.agent.background_task(group='queue_workflow_starter.py')
def start_workflow(settings, workflow_name, workflow_data):
    data_processor = workflow_data_processors.get(workflow_name)
    workflow_name = 'starter_' + workflow_name
    if data_processor is not None:
        workflow_data = data_processor(workflow_data)
    module_name = "starter." + workflow_name
    importlib.import_module(module_name)
    full_path = "starter." + workflow_name + "." + workflow_name + "()"
    starter_object = eval(full_path)
    starter_object.start(settings=settings, **workflow_data)


def process_data_ingestarticlezip(workflow_data):
    data = {'article_id': workflow_data['article_id'],
            'run': workflow_data['run'], 'version_reason': workflow_data.get('version_reason'),
            'scheduled_publication_date': workflow_data.get('scheduled_publication_date')}
    return data


def process_data_s3_notification_default(workflow_data):
    """definition for default data in response to an S3 notification"""
    data = {'info': S3NotificationInfo.from_dict(workflow_data),
            'run': str(uuid.uuid4())}
    return data


def process_data_initialarticlezip(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_postperfectpublication(workflow_data):
    data = {'info': workflow_data}
    return data


def process_data_pubmedarticledeposit(workflow_data):
    data = {}
    return data


def process_data_ingestdigest(workflow_data):
    return process_data_s3_notification_default(workflow_data)


def process_data_ingestdecisionletter(workflow_data):
    return process_data_s3_notification_default(workflow_data)


workflow_data_processors = {
    'IngestArticleZip': process_data_ingestarticlezip,
    'InitialArticleZip': process_data_initialarticlezip,
    'SilentCorrectionsIngest': process_data_initialarticlezip,
    'PostPerfectPublication': process_data_postperfectpublication,
    'PubmedArticleDeposit': process_data_pubmedarticledeposit,
    'IngestDigest': process_data_ingestdigest,
    'IngestDecisionLetter': process_data_ingestdecisionletter
}


def get_settings(env):
    import settings as settings_lib
    return settings_lib.get_settings(env)


def console_start():
    """capture options when running standalone"""
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    (options, args) = parser.parse_args()
    if options.env:
        env = options.env
        return env


if __name__ == "__main__":
    ENV = console_start()
    SETTINGS = get_settings(ENV)
    process.monitor_interrupt(lambda flag: main(SETTINGS, flag))
