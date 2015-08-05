"""
Process SQS message from queue and start required workflow
"""
import settings as settings_lib
from optparse import OptionParser
import log
import boto.sqs
from multiprocessing import Pool
import json
import dashboard_data_access

settings = None
logger = None


def main():
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    (options, args) = parser.parse_args()
    if options.env:
        env = options.env

    global settings
    settings = settings_lib.get_settings(env)

    log_file = "queue_workflow_starter.log"
    global logger
    logger = log.logger(log_file, settings.log_level)

    # Simple connect
    queue = get_queue()

    pool = Pool(settings.event_queue_pool_size)

    while True:
        messages = queue.get_messages(num_messages=settings.event_queue_message_count, visibility_timeout=60,
                                      wait_time_seconds=20)
        if messages is not None:
            logger.info(str(len(messages)) + " message received")
            pool.map(process_message, messages)
        else:
            logger.info("No messages received")


def get_queue():
    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.event_monitor_queue)
    return queue


def process_message(message):
    message_payload = json.loads(message.get_body())
    message_type = message_payload.get('message_type')
    if message_type is not None:
        if message_type in dispatch:
            dispatch[message_type](message_payload)
        else:
            logger.error('Unknown message type ' + message_type)
    message.delete()


def process_event_message(message):
    try:
        dashboard_data_access.store_event(message.get('version'), message.get('run'), message.get('event_type'),
                                          message.get('timestamp'), message.get('status'), message.get('message'),
                                          message.get('item_identifier'), message.get('message_id'))
    except Exception:
        logger.exception("Error processing event message ")


def process_property_message(message):
    try:
        dashboard_data_access.store_property(message.get('property_type'), message.get('name'), message.get('value'),
                                             message.get('item_identifier'), message.get('message_id'))
    except Exception:
        logger.exception("Error processing property message ")


def get_rds_connection():
    pass


dispatch = {'event': process_event_message, 'property': process_property_message}

if __name__ == "__main__":
    main()
