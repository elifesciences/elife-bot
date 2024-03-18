import json
from dateutil.parser import parse
import log
from provider import process
from provider import utils


IDENTITY = log.identity("lax_response_adapter")
LOGGER = log.logger("lax_response_adapter.log", "INFO", IDENTITY)


class ShortRetryException(RuntimeError):
    pass


class LaxResponseAdapter:
    def __init__(self, settings, logger):
        self._settings = settings
        self.logger = logger

    def listen(self, flag):
        self.logger.info("started")

        client = self._settings.aws_conn('sqs', {
            'aws_access_key_id': self._settings.aws_access_key_id,
            'aws_secret_access_key': self._settings.aws_secret_access_key,
            'region_name': self._settings.sqs_region,
        })

        input_queue_url_response = client.get_queue_url(
            QueueName=self._settings.lax_response_queue
        )
        input_queue_url = input_queue_url_response.get("QueueUrl")
        output_queue_url_response = client.get_queue_url(
            QueueName=self._settings.workflow_starter_queue
        )
        output_queue_url = output_queue_url_response.get("QueueUrl")

        if input_queue_url is not None:
            while flag.green():

                self.logger.debug("reading queue")
                queue_messages = client.receive_message(
                    QueueUrl=input_queue_url,
                    MaxNumberOfMessages=1,
                    VisibilityTimeout=60,
                    WaitTimeSeconds=20,
                )

                if queue_messages.get("Messages"):
                    queue_message = queue_messages.get("Messages")[0]
                    self.logger.info(
                        "got message id: %s", queue_message.get("MessageId")
                    )
                    try:
                        workflow_starter_message = self.process_message(queue_message)
                        # send workflow initiation message
                        self.logger.info(
                            "sending workflow starter message: %s",
                            workflow_starter_message,
                        )
                        client.send_message(
                            QueueUrl=output_queue_url,
                            MessageBody=json.dumps(workflow_starter_message),
                        )
                        self.logger.info(
                            "deleting message id: %s", queue_message.get("MessageId")
                        )
                        client.delete_message(
                            QueueUrl=input_queue_url,
                            ReceiptHandle=queue_message.get("ReceiptHandle"),
                        )
                    except ShortRetryException as exception:
                        self.logger.info(
                            "short retry: %s because of %s",
                            queue_message.get("MessageId"),
                            exception,
                        )
                        client.change_message_visibility(
                            QueueUrl=input_queue_url,
                            ReceiptHandle=queue_message.get("ReceiptHandle"),
                            VisibilityTimeout=10,
                        )

            self.logger.info("graceful shutdown")

        else:
            self.logger.error("Could not obtain queue, exiting")

    def process_message(self, message):
        message_str = str(message.get("Body"))
        return parse_message(message_str, self.logger)


def parse_token(token):
    "parse the token from a lax response message dict"
    try:
        token_parsed = utils.base64_decode_string(token)
        return json.loads(token_parsed)
    except:
        return {
            "run": None,
            "version": None,
            "expanded_folder": None,
            "status": None,
            "run_type": None,
        }


def parse_message(message, logger):
    "parse a lax response message"
    try:

        logger.info("got the following message from Lax: %s", message)

        message_data = json.loads(message)
        result = message_data["status"]

        date_time = parse(message_data["datetime"])
        date_time = date_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        article_id = message_data["id"]
        operation = message_data["requested-action"]
        response_message = None
        if "message" in message_data:
            response_message = message_data["message"]

        token = parse_token(message_data["token"])
        run = token["run"]
        version = token["version"]
        expanded_folder = token["expanded_folder"]
        status = token["status"]
        force = token["force"]
        run_type = token.get("run_type")

        workflow_data = {
            "run": run,
            "article_id": article_id,
            "version": version,
            "expanded_folder": expanded_folder,
            "status": status,  # vor/poa
            "result": result,
            "message": response_message,
            "update_date": date_time,
            "requested_action": operation,
            "force": force,
            "run_type": run_type,
        }

        if operation == "ingest":
            if "force" in token and token["force"] is True:
                workflow_starter_message = {
                    "workflow_name": "SilentCorrectionsProcess",
                    "workflow_data": workflow_data,
                }
                logger.info("calling workflow SilentCorrectionsProcess")
            else:
                workflow_starter_message = {
                    "workflow_name": "ProcessArticleZip",
                    "workflow_data": workflow_data,
                }
                logger.info("calling workflow ProcessArticleZip")
        else:
            workflow_starter_message = {
                "workflow_name": "PostPerfectPublication",
                "workflow_data": workflow_data,
            }

            logger.info("calling workflow PostPerfectPublication")

        return workflow_starter_message
    except Exception as exception:
        logger.error("Error parsing Lax message. Message: " + str(exception))
        raise


if __name__ == "__main__":
    ENV = utils.console_start_env()
    SETTINGS = utils.get_settings(ENV)
    lax_response_adapter = LaxResponseAdapter(SETTINGS, LOGGER)
    process.monitor_interrupt(lambda flag: lax_response_adapter.listen(flag))
