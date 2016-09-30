from optparse import OptionParser
import boto.sqs
import log
import json
from boto.sqs.message import Message
from provider import process

identity = log.identity('ingest_response_adapter')
logger = log.logger('ingest_response_adapter.log', 'INFO', identity)

class ShortRetryException(RuntimeError):
    pass


class IngestResponseAdapter:
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

            logger.info("graceful shutdown")

        else:
            self.logger.error("Could not obtain queue, exiting")

    def process_message(self, message, output_queue):

        message_data = json.loads(str(message.get_body()))
        run = message_data['token']
        status = message_data['status']
        date_time = message_data['datetime']
        article_id = message_data["id"]
        response_message = None
        if "message" in message_data:
            response_message = message_data["message"]

        workflow_data = {
            "run": run,
            "article_id": article_id,
            "status": status,
            "message": response_message,
            "date_time": date_time
        }

        workflow_starter_message = {
                "workflow_name": "ProcessArticleZip",
                "workflow_data": workflow_data
            }
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
    ingest_response_adapter = IngestResponseAdapter(settings, logger)
    process.monitor_interrupt(lambda flag: ingest_response_adapter.listen(flag))