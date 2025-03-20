import os
import json
import time
from activity.objects import Activity
from provider import (
    docmap_provider,
    github_provider,
    email_provider,
    utils,
)
from provider.execution_context import get_session
from provider.storage_provider import storage_context


# path to save docmap index in the bucket run folder
DOCMAP_INDEX_BUCKET_PATH = "docmap_index/docmap_index.json"


class activity_FindNewDocmaps(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindNewDocmaps, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindNewDocmaps"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 15
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Find new or recently modified docmaps, group data by version DOI, "
            "review, validate, save to S3, and start downstream workflows."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {}

        # Track XML files selected for pubmed XML
        self.good_xml_files = []
        self.bad_xml_files = []

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        "Activity, do the work" ""
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        run = data["run"]
        session = get_session(self.settings, data, run)
        new_run_docmap_index_resource = session.get_value(
            "new_run_docmap_index_resource"
        )
        prev_run_docmap_index_resource = session.get_value(
            "prev_run_docmap_index_resource"
        )

        # Create output directories
        self.make_activity_directories()

        # get previous run folder name from S3 bucket
        storage = storage_context(self.settings)

        # get docmap index JSON
        self.logger.info(
            "%s, getting new_run_docmap_index_resource %s as string"
            % (
                self.name,
                new_run_docmap_index_resource,
            )
        )
        docmap_index_json_string = storage.get_resource_as_string(
            new_run_docmap_index_resource
        )
        docmap_index_json = json.loads(docmap_index_json_string)

        # download previous docmap index file
        self.logger.info(
            "%s, getting prev_run_docmap_index_resource %s as string"
            % (
                self.name,
                prev_run_docmap_index_resource,
            )
        )

        prev_docmap_index_json = None
        if prev_run_docmap_index_resource:
            prev_docmap_index_json_content = storage.get_resource_as_string(
                prev_run_docmap_index_resource
            )
            prev_docmap_index_json = json.loads(prev_docmap_index_json_content)

        # compare previous docmap index to new docmap index
        docmap_data = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        ingest_version_doi_list = docmap_data.get("ingest_version_doi_list")
        self.logger.info(
            "%s, got ingest_version_doi_list: %s" % (self.name, ingest_version_doi_list)
        )
        self.statuses["generate"] = True

        # queue IngestMeca workflows
        if ingest_version_doi_list:
            self.logger.info(
                "%s, starting %s IngestMeca workflows"
                % (self.name, len(ingest_version_doi_list))
            )
            for version_doi in sorted(ingest_version_doi_list):
                doi, version = utils.version_doi_parts(version_doi)
                article_id = utils.msid_from_doi(doi)
                self.start_post_workflow(article_id, version)

        # add Github issue commment for docmaps with no computer-file
        no_computer_file_version_doi_list = docmap_data.get(
            "no_computer_file_version_doi_list"
        )
        self.logger.info(
            "%s, got no_computer_file_version_doi_list: %s"
            % (self.name, no_computer_file_version_doi_list)
        )
        for version_doi in no_computer_file_version_doi_list:
            issue_comment = (
                "No computer-file found in the docmap for version DOI %s" % version_doi
            )
            github_provider.add_github_issue_comment(
                self.settings, self.logger, self.name, version_doi, issue_comment
            )

        # determine the success of the activity
        self.statuses["activity"] = self.statuses.get("generate")

        # send email only if new XML files were generated
        if self.statuses.get("generate") and ingest_version_doi_list:
            self.logger.info("%s, sending admin email" % self.name)
            self.statuses["email"] = self.send_admin_email(ingest_version_doi_list)
        else:
            self.logger.info("%s, no new DOI versions found" % self.name)

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def send_admin_email(self, ingest_version_doi_list):
        "after do_activity is finished, send emails to admin with the status"
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        activity_status_text = utils.get_activity_status_text(
            self.statuses.get("activity")
        )

        body = email_provider.get_email_body_head(
            self.name, activity_status_text, self.statuses
        )

        # Report on new MECA files
        if len(ingest_version_doi_list) > 0:
            body += "\nVersion DOI with MECA file to ingest:\n"
            for version_doi in sorted(ingest_version_doi_list):
                body += "%s\n" % version_doi

        body += email_provider.get_admin_email_body_foot(
            self.get_activityId(),
            self.get_workflowId(),
            datetime_string,
            self.settings.domain,
        )

        subject = email_provider.get_email_subject(
            datetime_string,
            activity_status_text,
            self.name,
            self.settings.domain,
            ingest_version_doi_list,
        )
        sender_email = self.settings.ses_poa_sender_email

        recipient_email_list = email_provider.list_email_recipients(
            self.settings.ses_admin_email
        )

        for email in recipient_email_list:
            # Add the email to the email queue
            message = email_provider.simple_message(
                sender_email, email, subject, body, logger=self.logger
            )

            email_provider.smtp_send_messages(
                self.settings, messages=[message], logger=self.logger
            )
            self.logger.info(
                "Email sending details: admin email, email %s, to %s"
                % (self.name, email)
            )

        return True

    def start_post_workflow(self, article_id, version):
        "start a workflow after a preprint is first published"
        # build message
        workflow_name = "IngestMeca"
        workflow_data = {
            "article_id": article_id,
            "version": version,
            "standalone": False,
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
