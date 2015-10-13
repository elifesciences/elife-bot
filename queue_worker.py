import random
import time
import json
from multiprocessing import Process
from optparse import OptionParser
from S3utility.s3_notification_info import S3NotificationInfo
from S3utility.s3_sqs_message import S3SQSMessage
import boto.sqs
from boto.sqs.message import Message
import settings as settings_lib
import log
import os
import yaml
import re

# Add parent directory for imports, so activity classes can use elife-api-prototype
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

"""
Amazon SQS worker
"""


def work(ENV="dev"):
    # Specify run environment settings
    settings = settings_lib.get_settings(ENV)

    # Log
    identity = "queue_worker_%s" % int(random.random() * 1000)
    log_file = "queue_worker.log"
    # logFile = None
    logger = log.logger(log_file, settings.setLevel, identity)
    # TODO : better logging

    # Simple connect
    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.S3_monitor_queue)
    queue.set_message_class(S3SQSMessage)

    rules = load_rules()

    # Poll for an activity task indefinitely
    if queue is not None:
        while True:

            logger.info('reading message')
            queue_message = queue.read(30)
            # TODO : check for more-than-once delivery
            # ( Dynamo conditional write? http://tinyurl.com/of3tmop )

            if queue_message is None:
                logger.info('no messages available')
            else:
                logger.info('got message id: %s' % queue_message.id)
                if queue_message.notification_type == 'S3Event':
                    info = S3NotificationInfo.from_S3SQSMessage(queue_message)
                    starter_name = get_starter_name(rules, info)
                    module_name = 'starter.' + starter_name
                    if module_name is None:
                        logger.info("Could not handle file %s in bucket %s" % (info.file_name, info.bucket_name))
                        return False

                    # TODO : place message in queue

                    message = {
                        'workflow_name': "PublishPerfectArticle",
                        'workflow_data': info.to_dict()
                    }

                    out_queue = conn.get_queue(settings.workflow_starter_queue)

                    m = Message()
                    m.set_body(json.dumps(message))
                    out_queue.write(m)
                    logger.info("cancelling message")
                    queue.delete_message(queue_message)
                    logger.info("message cancelled")
                else:
                    # TODO : log
                    pass
            time.sleep(10)

    else:
        logger.error('error obtaining queue')


def load_rules():
    # load the rules from the YAML file
    stream = file('newFileWorkflows.yaml', 'r')
    return yaml.load(stream)


def get_starter_name(rules, info):
    for rule_name in rules:
        rule = rules[rule_name]
        if re.match(rule['bucket_name_pattern'], info.bucket_name) and \
                re.match(rule['file_name_pattern'], info.file_name):
            return rule['starter_name']
        pass


def reload_module(module_name):
    """
    Given an module name,
    attempt to reload the module
    """
    try:
        reload(eval(module_name))
    except:
        pass


def start_single_thread(ENV):
    """
    Start in single process / threaded mode, but
    return a pool resource of None to indicate it
    is running in a single thread
    """
    print 'starting single thread'
    work(ENV)
    return None


def start_multiple_thread(ENV):
    """
    Start multiple processes using a manual pool
    """
    pool = []
    for num in range(forks):
        p = Process(target=work, args=(ENV,))
        p.start()
        pool.append(p)
        print 'started worker thread'
        # Sleep briefly so polling connections do not happen at once
        time.sleep(0.5)
    return pool


def monitor_KeyboardInterrupt(pool=None):
    # Monitor for keyboard interrupt ctrl-C
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print 'caught KeyboardInterrupt, terminating threads'
        if pool != None:
            for p in pool:
                p.terminate()
        return False
    return True


if __name__ == "__main__":

    forks = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    parser.add_option("-f", "--forks", default=10, action="store", type="int", dest="forks",
                      help="specify the number of forks to start")
    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.forks:
        forks = options.forks

    pool = None
    # try:
    if forks > 1:
        pool = start_multiple_thread(ENV)
    else:
        start_single_thread(ENV)
        # except:
        # If forks is not specified start in single threaded mode
        # TODO : resolve issue when exception in thread. This whole area needs revisiting
        #    pass
        # start_single_thread(ENV)

    # Monitor for keyboard interrupt ctrl-C
    loop = True
    while loop:
        loop = monitor_KeyboardInterrupt(pool)
