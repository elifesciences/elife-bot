import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import time

from provider import utils
import starter.starter_helper as helper
from S3utility.s3_notification_info import S3NotificationInfo
from S3utility.s3_sqs_message import S3SQSMessage


"""
Cron job to check for new article S3 POA and start workflows
"""

MAX_MESSAGE_COUNT = 100


class cron_NewS3POA(object):

    def start(self, settings):

        ping_marker_id = "cron_NewS3POA"

        # Log
        logFile = "starter.log"
        logger = log.logger(logFile, settings.setLevel, ping_marker_id)

        # Start a ping workflow as a marker
        helper.start_ping_marker(ping_marker_id, settings, logger)

        # Get data from SQS queue
        sqs_conn = sqs_connect(settings)
        sqs_queue = get_sqs_queue(sqs_conn, settings)
        process_queue(sqs_queue, settings, logger)


def sqs_connect(settings):
    """connect to the queue service"""
    return boto.sqs.connect_to_region(
        settings.sqs_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key)


def get_sqs_queue(sqs_conn, settings):
    """get the queue"""
    queue = sqs_conn.get_queue(settings.poa_incoming_queue)
    queue.set_message_class(S3SQSMessage)
    return queue


def process_queue(sqs_queue, settings, logger):
    """reach each message from the queue, start a workflow, then delete the message"""
    messages = None
    if sqs_queue:
        messages = sqs_queue.get_messages(MAX_MESSAGE_COUNT)
    if not messages:
        logger.info('no messages available')
        return
    for message in messages:
        if message.notification_type == 'S3Event':
            result = start_package_poa_workflow(message, settings, logger)
            if result:
                sqs_queue.delete_message(message)


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
        logger.info('Started %s workflow for document %s' % (starter_name, document))
        return True
    except:
        logger.exception('Error: starting %s for document %s' % (starter_PackagePOA, document))


if __name__ == "__main__":

    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)

    o = cron_NewS3POA()

    o.start(settings=SETTINGS)
