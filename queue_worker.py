import random
import time
import importlib
from multiprocessing import Process
from optparse import OptionParser
from S3utility.s3_notification_info import S3NotificationInfo
from S3utility.s3_sqs_message import S3SQSMessage
import boto.sqs
from boto.sqs.jsonmessage import JSONMessage
import settings as settingsLib
import log
import os


# this is not an unused import, it is used dynamically
import starter

# Add parent directory for imports, so activity classes can use elife-api-prototype
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

"""
Amazon SQS worker
"""


def work(ENV="dev"):
    # Specify run environment settings
    settings = settingsLib.get_settings(ENV)

    # Log
    identity = "queue_worker_%s" % int(random.random() * 1000)
    log_file = "queue_worker.log"
    # logFile = None
    logger = log.logger(log_file, settings.setLevel, identity)
    # TODO : better logging

    # Simple connect
    conn = boto.sqs.connect_to_region(settings.jr_sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.jr_S3_monitor_queue)
    queue.set_message_class(S3SQSMessage)

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
                    bucket = info.bucket_name
                    filename = info.file_name
                    logger.info("%s received %s" % (bucket, filename))
                    starter_name = 'starter_NewS3File'
                    module_name = "starter." + starter_name
                    module = importlib.import_module(module_name)
                    reload_module(module)
                    full_path = "starter." + starter_name + "." + starter_name + "()"
                    s = eval(full_path)
                    s.start(ENV=ENV, info=info)
                    logger.info("cancelling message")
                    queue.delete_message(queue_message)
                    logger.info("message cancelled")
                else:
                    # TODO : log
                    pass
            time.sleep(10)

    else:
        logger.error('error obtaining queue')


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
        #except:
        # If forks is not specified start in single threaded mode
        # TODO : resolve issue when exception in thread. This whole area needs revisiting
        #    pass
        # start_single_thread(ENV)

    # Monitor for keyboard interrupt ctrl-C
    loop = True
    while loop:
        loop = monitor_KeyboardInterrupt(pool)


