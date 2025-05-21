import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import outbox_provider, preprint
from activity.objects import Activity


class activity_ConfirmPreprintPDF(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ConfirmPreprintPDF, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ConfirmPreprintPDF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Confirm a preprint PDF exists and then start"
            " or queue the next downstream workflow"
        )

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket
        self.outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder("FinishPreprintPublication")
        )

        self.statuses = {}

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        pdf_url = session.get_value("pdf_url")
        run_type = session.get_value("run_type")

        self.logger.info(
            "%s, for article_id %s version %s found pdf_url %s"
            % (self.name, article_id, version, pdf_url)
        )

        # if pdf_url, add a message to the workflow starter queue
        if pdf_url:
            self.start_post_publication_workflow(article_id, version, pdf_url, run_type)
        else:
            # if no pdf_url, queue the preprint version into an S3 bucket outbox folder
            self.add_to_outbox(
                self.publish_bucket,
                article_id,
                version,
                self.outbox_folder,
            )

        return self.ACTIVITY_SUCCESS

    def start_post_publication_workflow(self, article_id, version, pdf_url, run_type):
        "start a workflow after a preprint is published"
        # build message
        workflow_name = "FinishPreprintPublication"
        workflow_data = {
            "article_id": article_id,
            "version": version,
            "run_type": run_type,
            "pdf_url": pdf_url,
            "standalone": False,
        }
        message = {
            "workflow_name": workflow_name,
            "workflow_data": workflow_data,
            "execution_start_to_close_timeout": str(60 * 60),
        }
        self.logger.info(
            "%s, starting a %s workflow for article_id %s, version %s",
            self.name,
            workflow_name,
            article_id,
            version,
        )
        # connect to the queue
        queue_url = self.sqs_queue_url()
        # send workflow starter message
        self.sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )

    def sqs_connect(self):
        "connect to the queue service"
        if not self.sqs_client:
            self.sqs_client = self.settings.aws_conn(
                "sqs",
                {
                    "aws_access_key_id": self.settings.aws_access_key_id,
                    "aws_secret_access_key": self.settings.aws_secret_access_key,
                    "region_name": self.settings.sqs_region,
                },
            )

    def sqs_queue_url(self):
        "get the queues"
        self.sqs_connect()
        queue_url_response = self.sqs_client.get_queue_url(
            QueueName=self.settings.workflow_starter_queue
        )
        return queue_url_response.get("QueueUrl")

    def add_to_outbox(self, dest_bucket_name, article_id, version, prefix):
        "create preprint XML file name and add to the S3 bucket outbox folder"
        key_name = preprint.xml_filename(article_id, self.settings, version=version)
        body = b""
        bucket_resource = (
            self.settings.storage_provider
            + "://"
            + dest_bucket_name
            + "/"
            + prefix
            + key_name
        )
        storage = storage_context(self.settings)
        storage.set_resource_from_string(bucket_resource, body)
