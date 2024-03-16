import os
import datetime
import json
import time
import glob
import boto3
from activity.objects import CleanerBaseActivity
from provider import (
    bigquery,
    cleaner,
    email_provider,
    outbox_provider,
    preprint,
    utils,
)
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
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Bucket for published files
        self.publish_bucket = settings.poa_packaging_bucket
        self.bucket_folder = self.s3_bucket_folder(self.name) + "/"

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

        # check for required settings
        if not self.settings.epp_data_bucket:
            self.logger.info(
                "epp_data_bucket in settings is blank, skipping %s." % self.name
            )
            return True

        # Create output directories
        self.make_activity_directories()

        date_string = datetime.datetime.utcnow().strftime(utils.PUB_DATE_FORMAT)

        # BigQuery
        try:
            bigquery_client = bigquery.get_client(self.settings, self.logger)
            query_result = bigquery.preprint_article_result(
                bigquery_client, date_string=date_string, day_interval=DAY_INTERVAL
            )
            preprints = bigquery.preprint_objects(query_result)
        except Exception as exception:
            self.logger.exception(
                "%s, exception in GET request to BigQuery: %s"
                % (self.name, str(exception))
            )
            return True

        self.logger.info(
            "%s, got %s preprints from BigQuery" % (self.name, len(preprints))
        )

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # generate preprint file names and details
        xml_filename_detail_map = self.detail_map(preprints)
        self.logger.info(
            "%s, looking for XML filenames: %s"
            % (self.name, xml_filename_detail_map.keys())
        )

        # get a list of files from the published bucket
        new_xml_filenames = self.new_file_names(xml_filename_detail_map)
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

        # generate preprint XML for each, log when any XML file cannot be created
        self.generate_xml_files(new_xml_map)
        self.statuses["generate"] = bool(self.good_xml_files)

        # start a workflow for the new article version
        if self.statuses.get("generate") is True:
            for new_xml_filename, detail in new_xml_map.items():
                if new_xml_filename in self.good_xml_files:
                    self.start_post_workflow(
                        detail.get("article_id"), detail.get("version")
                    )

        # upload the new preprint XML to the published bucket folder
        if self.statuses.get("generate") is True:
            # Clean up outbox
            self.logger.info(
                "%s, copying new XML files to the bucket folder" % self.name
            )
            to_folder = self.bucket_folder
            # copy the XML files to the bucket
            batch_file_names = glob.glob(self.directories.get("OUTPUT_DIR") + "/*.xml")
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
        else:
            self.logger.info(
                "%s, no new XML files created. bad_xml_files: %s"
                % (self.name, self.bad_xml_files)
            )

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        self.end_cleaner_log(session=None)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def detail_map(self, preprints):
        "for each preprint, generate the expected XML file name, return a map of it and details"
        xml_filename_detail_map = {}
        for preprint_object in preprints:
            article_id = preprint_object.doi.rsplit(".", 1)[-1]
            xml_filename = preprint.xml_filename(
                article_id, self.settings, version=preprint_object.version
            )
            xml_filename_detail_map[xml_filename] = {
                "article_id": article_id,
                "version": preprint_object.version,
            }
        return xml_filename_detail_map

    def existing_file_names(self):
        "get a list of files from a bucket folder"
        storage = storage_context(self.settings)
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

    def new_file_names(self, xml_filename_detail_map):
        "return a list of file names not already found in the bucket folder"
        new_xml_filenames = [
            filename
            for filename in xml_filename_detail_map
            if filename not in self.existing_file_names()
        ]
        return new_xml_filenames

    def generate_xml_files(self, new_xml_map):
        "generate XML files for each new article"
        for new_xml_filename, detail in new_xml_map.items():
            self.logger.info(
                "%s, starting to generate preprint XML for "
                "article_id %s, version %s, to XML file name %s"
                % (
                    self.name,
                    detail.get("article_id"),
                    detail.get("version"),
                    new_xml_filename,
                )
            )

            # get the docmap_string for the article
            identifier = "%s-%s-v%s" % (
                self.name,
                detail.get("article_id"),
                detail.get("version"),
            )
            try:
                docmap_string = cleaner.get_docmap_string_with_retry(
                    self.settings,
                    detail.get("article_id"),
                    self.name,
                    self.logger,
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception getting the docmap_string for article_id %s, %s: %s"
                    % (self.name, detail.get("article_id"), identifier, str(exception))
                )
                self.bad_xml_files.append(new_xml_filename)
                continue

            # build the article object
            try:
                article_object = preprint.build_preprint_article(
                    self.settings,
                    detail.get("article_id"),
                    detail.get("version"),
                    docmap_string,
                    self.directories.get("TMP_DIR"),
                    self.logger,
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, failed to build the article_object for article_id %s: %s"
                    % (self.name, detail.get("article_id"), str(exception))
                )
                self.bad_xml_files.append(new_xml_filename)
                continue

            try:
                # write the article object to XML file
                xml_file_path = os.path.join(
                    self.directories.get("OUTPUT_DIR"), new_xml_filename
                )
                xml_string = preprint.preprint_xml(article_object, self.settings)
                with open(xml_file_path, "wb") as open_file:
                    open_file.write(xml_string)
            except Exception as exception:
                self.logger.exception(
                    "%s, failed to generate preprint XML"
                    " from the article_object for article_id %s: %s"
                    % (self.name, detail.get("article_id"), str(exception))
                )
                self.bad_xml_files.append(new_xml_filename)
                continue

            self.good_xml_files.append(new_xml_filename)

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
            self.good_xml_files,
            self.bad_xml_files,
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
            "standalone": True,
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
            self.sqs_client = boto3.client(
                "sqs",
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                region_name=self.settings.sqs_region,
            )

    def sqs_queue_url(self):
        "get the queues"
        self.sqs_connect()
        queue_url_response = self.sqs_client.get_queue_url(
            QueueName=self.settings.workflow_starter_queue
        )
        return queue_url_response.get("QueueUrl")
