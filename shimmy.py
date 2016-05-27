from optparse import OptionParser
import boto.sqs
from boto.sqs.message import Message
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import requests
from requests.auth import HTTPBasicAuth
import logging
import settings as settings_lib
import json

settings = None
logging.basicConfig(filename='shimmy.log', level=logging.DEBUG)


def listen():

    global settings
    settings = settings_lib.get_settings(ENV)

    conn = boto.sqs.connect_to_region(settings.sqs_region,
                                      aws_access_key_id=settings.aws_access_key_id,
                                      aws_secret_access_key=settings.aws_secret_access_key)
    input_queue = conn.get_queue(settings.website_ingest_queue)
    output_queue = conn.get_queue(settings.workflow_starter_queue)

    if input_queue is not None:
        while True:

            logging.debug('reading queue')
            queue_message = input_queue.read(30)

            if queue_message is None:
                logging.debug('no messages available')
            else:
                logging.debug('got message id: %s' % queue_message.id)

                process_message(queue_message, output_queue)
                queue_message.delete()

    else:
        logging.error("Could not obtain queue, exiting")


def process_message(message, output_queue):

    # extract parameters from message
    bucket = message.get("eif_bucket")
    filename = message.get("eif_filename")
    passthrough = message.get("passthrough")

    if bucket is None or filename is None or passthrough is None:
        logging.error("Message format incorrect:")
        logging.error(message)
        return

    # slurp EIF file from S3 into memory
    eif = slurp_eif(bucket, filename)

    # call drupal with EIF
    ingest_endpoint = settings.drupal_EIF_endpoint
    auth = None
    if settings.drupal_update_user and settings.drupal_update_user != '':
        auth = requests.auth.HTTPBasicAuth(settings.drupal_update_user,
                                           settings.drupal_update_pass)
        logging.debug("Requests auth set for user %s", settings.drupal_update_user)
    headers = {'content-type': 'application/json'}
    response = requests.post(ingest_endpoint, data=eif, headers=headers, auth=auth)
    logging.debug("Reponse code was % . Reason was %s", response.status_code, response.status_code)

    if response.status_code == 200:

        ingest_publish = response.json().get('publish')
        response_message = {
            "workflow_name": "ArticleInformationSupplier",
            "workflow_data": message
        }
        response_message['workflow_data']['ingest_publish'] = ingest_publish

        m = Message()
        m.set_body(json.dumps(response_message))
        output_queue.write(m)

    else:
        logging.error("Status code from ingest is %s", response.status_code)
        logging.error("Article not sent for ingestion is %s", passthrough.get(""))


def slurp_eif(bucketname, filename):

    conn = S3Connection(settings.aws_access_key_id,
                        settings.aws_secret_access_key)

    bucket = conn.get_bucket(bucketname)
    key = Key(bucket)
    key.key = filename
    json_output = key.get_contents_as_string()
    return json_output


if __name__ == "__main__":

    ENV = None

    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
