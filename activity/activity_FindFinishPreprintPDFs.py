import json
import re
import time
from provider import outbox_provider, preprint, utils
from activity.objects import Activity


API_SLEEP_SECONDS = 1


class activity_FindFinishPreprintPDFs(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindFinishPreprintPDFs, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindFinishPreprintPDFs"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Find whether a PDF exists for a list of preprint versions and"
            " and start a workflow if found"
        )

        # Bucket for outgoing files
        self.publish_bucket = settings.poa_packaging_bucket

        # Track the success of some steps
        self.statuses = {
            "outbox_status": None,
            "activity_status": None,
        }

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "reviewed_preprint_api_endpoint"):
            self.logger.info(
                "%s, reviewed_preprint_api_endpoint in settings is missing, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.reviewed_preprint_api_endpoint:
            self.logger.info(
                "%s, reviewed_preprint_api_endpoint in settings is blank, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS

        # determine the outbox name
        workflow_name = "FinishPreprintPublication"
        outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder(workflow_name)
        )

        if outbox_folder is None:
            # fail the workflow if no outbox folders are found
            self.logger.error(
                "%s, outbox_folder %s, failing the workflow"
                % (self.name, outbox_folder)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.statuses["outbox_status"] = True

        # get files from the outbox
        outbox_s3_key_names = sorted(
            outbox_provider.get_outbox_s3_key_names(
                self.settings, self.publish_bucket, outbox_folder
            )
        )

        self.logger.info(
            "%s, outbox_folder %s, outbox_s3_key_names: %s"
            % (self.name, outbox_folder, outbox_s3_key_names)
        )

        # parse outbox files into article_id + version
        preprint_versions = []
        for key_name in outbox_s3_key_names:
            preprint_version = parse_preprint_xml_path(key_name)
            # add if there is article_id and version
            if preprint_version and preprint_version[0] and preprint_version[1]:
                preprint_versions.append(preprint_version)
        self.logger.info(
            "%s, parsed preprint_versions: %s" % (self.name, preprint_versions)
        )

        approved_preprint_versions = []
        # for each article_id + version, check for PDF exists
        for article_id, version in preprint_versions:
            # check if PDF exists according to the API
            url = self.settings.reviewed_preprint_api_endpoint.format(
                article_id=utils.pad_msid(article_id), version=version
            )
            self.logger.info("%s, get url %s" % (self.name, url))
            try:
                pdf_url = preprint.get_preprint_pdf_url(
                    url,
                    self.name,
                    user_agent=getattr(self.settings, "user_agent", None),
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception raised getting pdf_url from endpoint %s: %s"
                    % (self.name, url, str(exception))
                )
                pdf_url = None
            if pdf_url:
                approved_preprint_versions.append((article_id, version, pdf_url))
            # sleep a short time between requests
            time.sleep(API_SLEEP_SECONDS)

        self.logger.info(
            "%s, got approved_preprint_versions: %s"
            % (self.name, approved_preprint_versions)
        )

        if not approved_preprint_versions:
            self.logger.info("%s, no approved files found in the outbox" % (self.name))
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            self.clean_tmp_dir()
            return self.ACTIVITY_SUCCESS

        # for each PDF found, start a FinishPreprintPublication worklfow
        for approved_data in approved_preprint_versions:
            self.start_post_publication_workflow(
                article_id=approved_data[0],
                version=approved_data[1],
                pdf_url=approved_data[2],
                run_type=None,
            )

        self.statuses["activity_status"] = True

        # Clean up disk
        self.clean_tmp_dir()

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

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
            "%s, starting a %s workflow for article_id %s, version %s, with pdf_url %s",
            self.name,
            workflow_name,
            article_id,
            version,
            pdf_url,
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


def parse_preprint_xml_path(key_name):
    "parse the article_id and version from a preprint XML outbox bucket key name"
    file_name = key_name.rsplit("/", 1)[-1]
    matches = re.match(r"elife-preprint-(\d+)-v(\d+).xml", file_name)
    try:
        return matches[1], matches[2]
    except (IndexError, TypeError):
        return None, None
