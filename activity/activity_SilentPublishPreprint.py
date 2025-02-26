import datetime
import json
from activity.objects import Activity
from provider.execution_context import get_session
from provider import cleaner, utils


class activity_SilentPublishPreprint(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_SilentPublishPreprint, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "SilentPublishPreprint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Check the publication status of the preprint version which was silent ingested,"
            " and start a post-publicatoin workflow if it is published status"
        )

        # Track the success of some steps
        self.statuses = {}

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        "Activity, do the work" ""
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        version_doi = session.get_value("version_doi")
        doi, version = utils.version_doi_parts(version_doi)
        article_id = utils.msid_from_doi(doi)
        docmap_string = session.get_value("docmap_string")

        # determine if published (based on docmap data ?)
        history_data = cleaner.docmap_preprint_history_from_docmap(docmap_string)
        published_date_string = None
        for history_data_dict in history_data:
            if history_data_dict.get("doi") == version_doi:
                published_date_string = history_data_dict.get("published")
                self.statuses["published_date"] = True
        if not published_date_string:
            self.logger.info(
                (
                    "%s, no published date found in the docmap for version DOI %s,"
                    " no silent-correction PostPreprintPublication workflow will be started"
                )
                % (self.name, version_doi)
            )
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            return True

        # compare the published datetime
        published_datetime = datetime.datetime.strptime(
            published_date_string, "%Y-%m-%dT%H:%M:%S%z"
        )
        current_datetime = utils.get_current_datetime()
        if current_datetime - published_datetime < datetime.timedelta(hours=0):
            self.logger.info(
                (
                    "%s, published datetime %s in the docmap for version DOI %s"
                    " is greater than the current datetime %s, no silent-correction"
                    " PostPreprintPublication workflow will be started"
                )
                % (self.name, published_datetime, version_doi, current_datetime)
            )
            self.statuses["approved"] = False
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            return True
        self.statuses["approved"] = True

        # start a silent-correction PostPreprintPublication workflow for the article version
        self.start_post_workflow(article_id, version)
        self.statuses["queued"] = True

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def start_post_workflow(self, article_id, version):
        "start a workflow after a preprint is first published"
        # build message
        workflow_name = "PostPreprintPublication"
        workflow_data = {
            "article_id": article_id,
            "version": version,
            "standalone": False,
            "run_type": "silent-correction",
        }
        message = {
            "workflow_name": workflow_name,
            "workflow_data": workflow_data,
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
