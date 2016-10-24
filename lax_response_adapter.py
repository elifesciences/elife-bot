from optparse import OptionParser
import boto.sqs
import log
import json
from boto.sqs.message import Message
from provider import process
import base64
from dateutil.parser import parse

identity = log.identity('lax_response_adapter')
logger = log.logger('lax_response_adapter.log', 'INFO', identity)

class ShortRetryException(RuntimeError):
    pass


class LaxResponseAdapter:
    def __init__(self, settings, logger):
        self._settings = settings
        self.logger = logger

    def listen(self, flag):
        self.logger.info("started")
        conn = boto.sqs.connect_to_region(self._settings.sqs_region,
                                          aws_access_key_id=self._settings.aws_access_key_id,
                                          aws_secret_access_key=self._settings.aws_secret_access_key)
        input_queue = conn.get_queue(self._settings.lax_response_queue)
        output_queue = conn.get_queue(self._settings.workflow_starter_queue)
        if input_queue is not None:
            while flag.green():

                self.logger.debug('reading queue')
                queue_message = input_queue.read(visibility_timeout=60, wait_time_seconds=20)
                if queue_message is not None:
                    self.logger.info('got message id: %s', queue_message.id)
                    try:
                        self.process_message(queue_message, output_queue)
                        queue_message.delete()
                    except ShortRetryException as e:
                        self.logger.info('short retry: %s because of %s', queue_message.id, e)
                        queue_message.change_visibility(visibility_timeout=10)

            self.logger.info("graceful shutdown")

        else:
            self.logger.error("Could not obtain queue, exiting")

    def parse_token(self, token):
        try:
            token_parsed = base64.decodestring(token)
            return json.loads(token_parsed)
        except:
            return {
                "run": None,
                "version": None,
                "expanded_folder": None,
                "status": None,
                "eif_location": None
            }

    def parse_message(self, message):
        try:

            self.logger.info('got the following message from Lax: %s', message)

            message_data = json.loads(message)
            result = message_data['status']

            date_time = parse(message_data['datetime'])
            date_time = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            article_id = message_data["id"]
            operation = message_data["requested-action"]
            response_message = None
            if "message" in message_data:
                response_message = message_data["message"]

            token = self.parse_token(message_data['token'])
            run = token['run']
            version = token['version']
            expanded_folder = token['expanded_folder']
            status = token['status']
            eif_location = token['eif_location'] #support for old journal
            force = token['force']

            workflow_data = {
                "run": run,
                "article_id": article_id,
                "version": version,
                "expanded_folder": expanded_folder,
                "status": status, #vor/poa
                "eif_location": eif_location,
                "result": result,
                "message": response_message,
                "update_date": date_time,
                "requested_action": operation
            }

            if operation == "ingest":
                if force == True:
                    workflow_starter_message = {
                            "workflow_name": "SilentCorrectionsProcess",
                            "workflow_data": workflow_data
                        }
                else:
                    workflow_starter_message = {
                            "workflow_name": "ProcessArticleZip",
                            "workflow_data": workflow_data
                        }
            else:
                workflow_starter_message = {
                        "workflow_name": "PostPerfectPublication",
                        "workflow_data": workflow_data
                    }

            return workflow_starter_message
        except Exception as e:
            self.logger.error("Error parsing Lax message. Message: " + e.message)
            raise

    def process_message(self, message, output_queue):
        message_str = str(message.get_body())
        workflow_starter_message = self.parse_message(message_str)

        m = Message()
        m.set_body(json.dumps(workflow_starter_message))
        output_queue.write(m)

if __name__ == "__main__":

    ENV = None

    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")

    (options, args) = parser.parse_args()
    ENV = options.env
    settings_lib = __import__('settings')
    settings = settings_lib.get_settings(ENV)
    lax_response_adapter = LaxResponseAdapter(settings, logger)
    process.monitor_interrupt(lambda flag: lax_response_adapter.listen(flag))