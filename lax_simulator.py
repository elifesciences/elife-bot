from optparse import OptionParser
import boto.sqs
import log
import json
from boto.sqs.message import Message
import datetime
from provider import process

identity = log.identity('lax_simulator')
logger = log.logger('lax_simulator.log', 'INFO', identity)

class ShortRetryException(RuntimeError):
    pass


class LaxSimulator:
    def __init__(self, settings, logger):
        self._settings = settings
        self.logger = logger

    def listen(self, flag):
        self.logger.info("started")
        conn = boto.sqs.connect_to_region(self._settings.sqs_region,
                                          aws_access_key_id=self._settings.aws_access_key_id,
                                          aws_secret_access_key=self._settings.aws_secret_access_key)
        input_queue = conn.get_queue(self._settings.xml_info_queue)
        output_queue = conn.get_queue(self._settings.lax_response_queue)
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
        article_id = message_data.get("id")
        token = message_data.get("token")
        action = message_data.get("action")

        # if action == "publish":
        #     response_message = {
        #         "requested-action": action,
        #         "status": "error",
        #         "message": "error is xxxxx",
        #         "id": article_id,
        #         "token": token,
        #         "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        #     }
        # else:
        #     response_message = {
        #             "requested-action": action,
        #             "status": action + "ed",
        #             "id": article_id,
        #             "token": token,
        #             "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        #         }

        response_message = {
                    "requested-action": action,
                    "status": action + "ed",
                    "id": article_id,
                    "token": token,
                    "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
        # response_message = {
        #         "requested-action": action,
        #         "status": "invalid",
        #         "message": "invalid data",
        #         "id": None,
        #         "token": None,
        #         "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        #     }

        m = Message()
        m.set_body(json.dumps(response_message))
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
    lax_simulator = LaxSimulator(settings, logger)
    process.monitor_interrupt(lambda flag: lax_simulator.listen(flag))
