import boto.sqs
import settings as settings_lib
from optparse import OptionParser
import log
from boto.s3.key import Key
from boto.s3.connection import S3Connection

settings = None


def listen(env="dev"):

    global settings

    settings = settings_lib.get_settings(env)

    log_file = "shimmy.log"
    logger = log.logger(log_file, settings.setLevel, None)

    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    queue = conn.get_queue(settings.S3_monitor_queue)

    if queue is not None:
        while True:

            logger.info('reading message')
            queue_message = queue.read(30)

            if queue_message is None:
                logger.debug('no messages available')
            else:
                logger.debug('got message id: %s' % queue_message.id)

                process_message(queue_message)

    else:
        logger.error("Could not obtain queue")


def process_message(message):

    # extract parameters from message
    bucket = ""
    filename = ""

    # slurp EIF file from S3 into memory
    slurp_eif(bucket, filename)

    # call drupal with EIF

    # if successful ingest

    #      construct response

    #      send response to workflow starter queu

    # else

    #      log

    #      alert?

    pass


def slurp_eif(bucketname, filename):

    conn = S3Connection(settings.aws_access_key_id,
                        settings.aws_secret_access_key)

    bucket = conn.get_bucket(bucketname)
    key = Key(bucket)
    key.key = filename
    json_output = key.get_contents_as_string()


if __name__ == "__main__":
    forks = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
