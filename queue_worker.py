import json
import random
import time
import importlib
from multiprocessing import Process
from optparse import OptionParser
from s3_sqs_message import S3SQSMessage

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
Amazon SWF worker
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
    # TODO : set queue message type to a custom S3EventNotification subclass extending boto.sqs.message

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
                bucket = queue_message.bucket_name()
                filename = queue_message.file_name()
                print "%s received %s" % (bucket, filename)

                # TODO : create initial workflow to handle new objects in S3
                # TODO : m  ake that workflow configurable to choose a second workflow based on bucket name,
                # TODO (cont) file name and maybe contents

                starter_name = 'starter_NewS3File'
                module_name = "starter." + starter_name
                module = importlib.import_module(module_name)
                reload_module(module)
                full_path = "starter." + starter_name + "." + starter_name + "()"
                s = eval(full_path)
                # TODO : etag too?
                s.start(ENV=ENV, bucket=bucket, filename=filename)
                print "cancelling message"
                queue.delete_message(queue_message)
                print "message cancelled"
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


