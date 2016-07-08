from optparse import OptionParser
import boto.sqs
from boto.sqs.message import Message
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import requests
from requests.auth import HTTPBasicAuth
import logging
import json

logging.basicConfig(filename='shimmy.log', level=logging.INFO)

class ShortRetryException(RuntimeError):
    pass

class Shimmy:
    def __init__(self, settings):
        self._settings = settings

    def listen(self):
        logging.info("started")
        conn = boto.sqs.connect_to_region(self._settings.sqs_region,
                                          aws_access_key_id=self._settings.aws_access_key_id,
                                          aws_secret_access_key=self._settings.aws_secret_access_key)
        input_queue = conn.get_queue(self._settings.website_ingest_queue)
        output_queue = conn.get_queue(self._settings.workflow_starter_queue)
        if input_queue is not None:
            while True:

                logging.debug('reading queue')
                queue_message = input_queue.read(visibility_timeout=60, wait_time_seconds=20)

                if queue_message is not None:
                    logging.debug('got message id: %s', queue_message.id)
                    try:
                        self.process_message(queue_message, output_queue)
                        queue_message.delete()
                    except ShortRetryException as e:
                        logging.info('short retry: %s because of %s', queue_message.id, e)
                        queue_message.change_visibility(visibility_timeout=10)

        else:
            logging.error("Could not obtain queue, exiting")


    def process_message(self, message, output_queue):

        # extract parameters from message
        message_data = json.loads(str(message.get_body()))
        bucket = message_data.get("eif_bucket")
        filename = message_data.get("eif_filename")
        passthrough = message_data.get("passthrough")

        if bucket is None or filename is None or passthrough is None:
            logging.error("Message format incorrect:")
            logging.error(message_data)
            return

        # slurp EIF file from S3 into memory
        eif = self.slurp_eif(bucket, filename)
        self.post_eif(eif, bucket, filename, passthrough, output_queue)

    def post_eif(self, eif, bucket, filename, passthrough, output_queue):
        # call drupal with EIF
        ingest_endpoint = self._settings.drupal_EIF_endpoint
        auth = None
        if self._settings.drupal_update_user and self._settings.drupal_update_user != '':
            auth = requests.auth.HTTPBasicAuth(self._settings.drupal_update_user,
                                               self._settings.drupal_update_pass)
            logging.debug("Requests auth set for user %s", self._settings.drupal_update_user)
        headers = {'content-type': 'application/json'}
        response = requests.post(ingest_endpoint, data=eif, headers=headers, auth=auth)
        logging.debug("Reponse code was %s . Reason was %s", response.status_code, response.reason)

        if response.status_code == 200:

            ingest_publish = response.json().get('publish')
            workflow_data = {
                'eif_filename': filename,
                'eif_bucket':  bucket,
                'article_id': passthrough.get("article_id"),
                'version': passthrough.get("version"),
                'run': passthrough.get("run"),
                'article_path': passthrough.get("article_path"),
                'expanded_folder': passthrough.get("expanded_folder"),
                'status': passthrough.get("status"),
                'update_date': passthrough.get("update_date"),
                'published': ingest_publish
            }
            response_message = {
                "workflow_name": "ArticleInformationSupplier",
                "workflow_data": workflow_data
            }

            m = Message()
            m.set_body(json.dumps(response_message))
            output_queue.write(m)
        elif response.status_code == 429:
            raise ShortRetryException("Response code was %s" % response.status_code)
        else:
            logging.error("Status code from ingest is %s", response.status_code)
            logging.error("Article not sent for ingestion %s", passthrough.get("article_id"))


    def slurp_eif(self, bucketname, filename):

        conn = S3Connection(self._settings.aws_access_key_id,
                            self._settings.aws_secret_access_key)

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
        settings_lib = __import__('settings')
        settings = settings_lib.get_settings(ENV)
        shimmy = Shimmy(settings)
        shimmy.listen()
