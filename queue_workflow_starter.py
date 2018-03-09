"""
Process SQS message from queue and start required workflow
"""
from S3utility.s3_notification_info import S3NotificationInfo
import settings as settings_lib
from optparse import OptionParser
import log
import boto.sqs
from provider import process
import json
import importlib
import os
import uuid
import newrelic.agent

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

settings = None
logger = None


def main(flag):
    global settings
    global env
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    (options, args) = parser.parse_args()
    if options.env:
        env = options.env

    settings = settings_lib.get_settings(env)
    env = env

    log_file = "queue_workflow_starter.log"
    global logger
    identity = "queue_workflow_starter_%s" % os.getpid()
    logger = log.logger(log_file, settings.setLevel, identity=identity)

    # Simple connect
    queue = get_queue()

    while flag.green():
        messages = queue.get_messages(1, visibility_timeout=60,
                                      wait_time_seconds=20)
        if messages:
            logger.info(str(len(messages)) + " message received")
            logger.info('message contents: %s', messages[0])
            process_message(messages[0])
        else:
            logger.debug("No messages received")

    logger.info("graceful shutdown")

def get_queue():
    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.workflow_starter_queue)
    return queue


def process_message(message):
    try:
        message_payload = json.loads(str(message.get_body()))
        name = message_payload.get('workflow_name')
        data = message_payload.get('workflow_data')
        start_workflow(name, data)
    except Exception:
        logger.exception("Exception while processing message")
    message.delete()

@newrelic.agent.background_task(group='queue_workflow_starter.py')
def start_workflow(workflow_name, workflow_data):
    data_processor = workflow_data_processors.get(workflow_name)
    workflow_name = 'starter_' + workflow_name
    if data_processor is not None:
        workflow_data = data_processor(workflow_name, workflow_data)
    module_name = "starter." + workflow_name
    module = importlib.import_module(module_name)
    try:
        reload(eval(module))
    except:
        pass
    full_path = "starter." + workflow_name + "." + workflow_name + "()"
    s = eval(full_path)
    s.start(settings=settings, **workflow_data)

def process_data_ingestarticlezip(workflow_name, workflow_data):
    data = {'article_id': workflow_data['article_id'],
            'run': workflow_data['run'], 'version_reason': workflow_data.get('version_reason'),
            'scheduled_publication_date': workflow_data.get('scheduled_publication_date')}
    return data

def process_data_initialarticlezip(workflow_name, workflow_data):
    data = {'info': S3NotificationInfo.from_dict(workflow_data),
            'run': str(uuid.uuid4())}
    return data

def process_data_postperfectpublication(workflow_name, workflow_data):
    data = {'info': workflow_data}
    return data

def process_data_pubmedarticledeposit(workflow_name, workflow_data):
    data = {}
    return data

workflow_data_processors = {
    'IngestArticleZip': process_data_ingestarticlezip,
    'InitialArticleZip': process_data_initialarticlezip,
    'SilentCorrectionsIngest': process_data_ingestarticlezip,
    'PostPerfectPublication': process_data_postperfectpublication,
    'PubmedArticleDeposit': process_data_pubmedarticledeposit
}

if __name__ == "__main__":
    process.monitor_interrupt(main)
