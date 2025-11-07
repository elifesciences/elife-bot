import os
import datetime
import json
import time
import glob
from activity.objects import CleanerBaseActivity
from provider import (
    docmap_provider,
    email_provider,
    outbox_provider,
    preprint,
    utils,
)
from provider.execution_context import get_session
from provider.storage_provider import storage_context


DAY_INTERVAL = 7


class activity_FindNewPreprints(CleanerBaseActivity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindNewPreprints, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindNewPreprints"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 15
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Get a list of recently published preprint versions, "
            "check for ones that are published for the first time, "
            "and start downstream workflows for them."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Bucket for published files
        self.publish_bucket = settings.poa_packaging_bucket
        self.bucket_folder = self.s3_bucket_folder(self.name) + "/"

        # Track the success of some steps
        self.statuses = {}

        # SQS client
        self.sqs_client = None

    def do_activity(self, data=None):
        "Activity, do the work" ""
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not self.settings.epp_data_bucket:
            self.logger.info(
                "epp_data_bucket in settings is blank, skipping %s." % self.name
            )
            return True

        # Create output directories
        self.make_activity_directories()

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        run = data["run"]
        session = get_session(self.settings, data, run)
        new_run_docmap_index_resource = session.get_value(
            "new_run_docmap_index_resource"
        )

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

        # get list of published article_id + version from docmap index JSON
        current_datetime = utils.get_current_datetime()
        xml_filename_detail_map = docmap_detail_map(
            docmap_index_json, current_datetime, DAY_INTERVAL, self.settings
        )

        self.logger.info(
            "%s, looking for XML filenames: %s"
            % (self.name, xml_filename_detail_map.keys())
        )

        # get a list of files from the published bucket
        new_xml_filenames = self.new_file_names(xml_filename_detail_map, storage)
        self.logger.info(
            "%s, found new_xml_filenames: %s" % (self.name, new_xml_filenames)
        )

        # return True now if there are no new XML files to generate
        if not new_xml_filenames:
            self.logger.info(
                "%s, all new_xml_filenames were already present in the bucket"
                % self.name
            )
            return True

        # create a map of the new XML file names
        new_xml_map = {
            xml_filename: details
            for xml_filename, details in xml_filename_detail_map.items()
            if xml_filename in new_xml_filenames
        }

        # generate status based on whether new XML files names were found
        self.statuses["generate"] = bool(new_xml_filenames)

        # start a workflow for the new article version
        if self.statuses.get("generate") is True:
            for new_xml_filename, detail in new_xml_map.items():
                if new_xml_filename in new_xml_filenames:
                    self.start_post_workflow(
                        detail.get("article_id"), detail.get("version")
                    )

        # upload the new preprint XML placeholder to the published bucket folder
        if self.statuses.get("generate") is True:
            self.logger.info(
                "%s, copying new XML files to the bucket folder" % self.name
            )

            # create placeholder XML files on disk
            for placeholder_file_name in new_xml_filenames:
                with open(
                    os.path.join(
                        self.directories.get("INPUT_DIR"), placeholder_file_name
                    ),
                    "wb",
                ) as open_file:
                    open_file.write(b"")

            to_folder = self.bucket_folder
            # copy the XML files to the bucket
            batch_file_names = glob.glob(self.directories.get("INPUT_DIR") + "/*.xml")
            outbox_provider.upload_files_to_s3_folder(
                self.settings,
                self.publish_bucket,
                to_folder,
                batch_file_names,
            )
            self.statuses["upload"] = True

        # determine the success of the activity
        self.statuses["activity"] = self.statuses["generate"]

        # send email only if new XML files were generated
        if self.statuses["generate"]:
            self.statuses["email"] = self.send_admin_email(new_xml_filenames)

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        self.end_cleaner_log(session=None)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def existing_file_names(self, storage):
        "get a list of files from a bucket folder"
        bucket_resource = (
            self.settings.storage_provider
            + "://"
            + self.publish_bucket
            + "/"
            + self.bucket_folder
        )
        s3_key_names = storage.list_resources(bucket_resource)
        # remove the bucket folder prefix from the s3 key names
        return [
            s3_key_name.rsplit(self.bucket_folder, 1)[-1]
            for s3_key_name in s3_key_names
        ]

    def new_file_names(self, xml_filename_detail_map, storage):
        "return a list of file names not already found in the bucket folder"
        existing_file_name_list = self.existing_file_names(storage)
        new_xml_filenames = [
            filename
            for filename in xml_filename_detail_map
            if filename not in existing_file_name_list
        ]
        return new_xml_filenames

    def send_admin_email(self, new_xml_filenames):
        "after do_activity is finished, send emails to admin with the status"
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        activity_status_text = utils.get_activity_status_text(
            self.statuses.get("activity")
        )

        body = email_provider.get_email_body_head(
            self.name, activity_status_text, self.statuses
        )
        body += email_provider.get_email_body_middle(
            "FindNewPreprints",
            new_xml_filenames,
            new_xml_filenames,
            [],
        )
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
            new_xml_filenames,
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
        workflow_name = "PostPreprintPublication"
        workflow_data = {
            "article_id": article_id,
            "version": version,
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


def docmap_detail_map(docmap_index_json, current_datetime, day_interval, settings):
    "find in the docmap index preprint versions published within the specified timeframe"
    xml_filename_detail_map = {}

    step_profile = docmap_provider.docmap_profile_step_map(docmap_index_json)

    for key, value in step_profile.items():
        if not value.get("published"):
            continue
        published_datetime = datetime.datetime.strptime(
            value.get("published"), "%Y-%m-%dT%H:%M:%S%z"
        )
        if current_datetime - published_datetime > datetime.timedelta(
            seconds=0
        ) and current_datetime - published_datetime < datetime.timedelta(
            days=day_interval
        ):
            doi, version = utils.version_doi_parts(key)
            article_id = utils.msid_from_doi(doi)
            xml_filename = preprint.xml_filename(article_id, settings, version=version)
            xml_filename_detail_map[xml_filename] = {
                "article_id": article_id,
                "version": version,
            }

    return xml_filename_detail_map
