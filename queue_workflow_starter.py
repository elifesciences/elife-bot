"""
Process SQS message from queue and start required workflow
"""
from S3utility.s3_notification_info import S3NotificationInfo
import settings as settings_lib
from optparse import OptionParser
import log
import boto.sqs
from multiprocessing import Pool
import json
import importlib

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


def main():
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
    logger = log.logger(log_file, settings.setLevel)

    # Simple connect
    queue = get_queue()

    pool = Pool(settings.workflow_starter_queue_pool_size, initialise_pool, [env])

    while True:
        messages = queue.get_messages(num_messages=settings.workflow_starter_queue_message_count, visibility_timeout=60,
                                      wait_time_seconds=20)
        if messages is not None:
            logger.info(str(len(messages)) + " message received")
            pool.map(process_message, messages)
        else:
            logger.debug("No messages received")

def initialise_pool(*args):
    """ Explicitly set each pool process global variable """
    global env
    env = args[0]

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
    s.start(ENV=env, **workflow_data)


def process_data_publishperfectarticle(workflow_name, workflow_data):
    data = {'info': S3NotificationInfo.from_dict(workflow_data)}
    return data


workflow_data_processors = {
    'PublishPerfectArticle': process_data_publishperfectarticle,
    'ArticleInformationSupplier': process_data_publishperfectarticle
}

if __name__ == "__main__":
    main()
