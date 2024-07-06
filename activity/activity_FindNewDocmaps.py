import os
from datetime import datetime
import json
import time
from activity.objects import Activity
from provider import (
    docmap_provider,
    email_provider,
    utils,
)
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
        if not hasattr(self.settings, "docmap_index_url"):
            self.logger.info(
                "%s, docmap_index_url in settings is missing, skipping" % self.name
            )
            return True
        if not self.settings.docmap_index_url:
            self.logger.info(
                "%s, docmap_index_url in settings is blank, skipping" % self.name
            )
            return True

        # Create output directories
        self.make_activity_directories()

        # get docmap index JSON
        try:
            docmap_index_json = docmap_provider.get_docmap_index_json(
                self.settings, self.name, self.logger
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting a docmap index: %s" % (self.name, str(exception))
            )
            return True
        if not docmap_index_json:
            self.logger.info("%s, docmap_index_json was None" % self.name)
            return True
        if not docmap_index_json.get("docmaps"):
            self.logger.info("%s, docmaps in docmap_index_json was empty" % self.name)
            return True

        docmap_index_json_path = os.path.join(
            self.directories.get("TEMP_DIR"), "docmap_index.json"
        )
        self.logger.info(
            "%s, saving docmap_index_json to %s" % (self.name, docmap_index_json_path)
        )
        with open(docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(docmap_index_json))

        # get previous run folder name from S3 bucket
        storage = storage_context(self.settings)
        run_folder_bucket_path = (
            self.settings.storage_provider
            + "://"
            + self.publish_bucket
            + "/"
            + self.bucket_folder
        )

        prev_run_folder = previous_run_folder(storage, run_folder_bucket_path)
        prev_run_folder_bucket_path = None
        self.logger.info("%s, prev_run_folder: %s" % (self.name, prev_run_folder))
        if prev_run_folder:
            prev_run_folder_bucket_path = "%s%s/" % (
                run_folder_bucket_path,
                prev_run_folder,
            )
        self.logger.info(
            "%s, prev_run_folder_bucket_path: %s"
            % (self.name, prev_run_folder_bucket_path)
        )

        # download previous docmap index file, continue
        prev_docmap_index_json_path = None
        if prev_run_folder_bucket_path:
            prev_docmap_index_json_path = os.path.join(
                self.directories.get("INPUT_DIR"), "prev_docmap_index.json"
            )
            prev_run_docmap_index_resource = "%s%s" % (
                prev_run_folder_bucket_path,
                DOCMAP_INDEX_BUCKET_PATH,
            )
            self.logger.info(
                "%s, saving %s to %s"
                % (
                    self.name,
                    prev_run_docmap_index_resource,
                    prev_docmap_index_json_path,
                )
            )
            with open(prev_docmap_index_json_path, "wb") as open_file:
                storage.get_resource_to_file(prev_run_docmap_index_resource, open_file)

        # parse previous docmap index file, continue (otherwise get the next previous run folder)
        prev_docmap_index_json = None
        if prev_docmap_index_json_path:
            self.logger.info(
                "%s, parsing %s into JSON" % (self.name, prev_docmap_index_json_path)
            )
            with open(prev_docmap_index_json_path, "rb") as open_file:
                prev_docmap_index_json_content = open_file.read()

            if prev_docmap_index_json_content:
                prev_docmap_index_json = json.loads(prev_docmap_index_json_content)

        # compare previous docmap index to new docmap index
        new_meca_version_dois = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.logger.info(
            "%s, got new_meca_version_dois: %s" % (self.name, new_meca_version_dois)
        )
        self.statuses["generate"] = True

        # queue IngestMeca workflows
        if new_meca_version_dois:
            self.logger.info(
                "%s, starting %s IngestMeca workflows"
                % (self.name, len(new_meca_version_dois))
            )
            for version_doi in new_meca_version_dois:
                doi, version = utils.version_doi_parts(version_doi)
                article_id = utils.msid_from_doi(doi)
                self.start_post_workflow(article_id, version)

        # new run folder name, based on the immediately previous run folder name
        new_run_folder_name = new_run_folder(storage, run_folder_bucket_path)
        new_run_docmap_index_resource = "%s%s/%s" % (
            run_folder_bucket_path,
            new_run_folder_name,
            DOCMAP_INDEX_BUCKET_PATH,
        )
        self.logger.info(
            "%s, new_run_docmap_index_resource: %s"
            % (self.name, new_run_docmap_index_resource)
        )

        # upload docmap index JSON to the new run folder name in the S3 bucket
        self.logger.info(
            "%s, storing %s to %s"
            % (self.name, docmap_index_json_path, new_run_docmap_index_resource)
        )
        storage.set_resource_from_filename(
            new_run_docmap_index_resource, docmap_index_json_path
        )
        self.statuses["upload"] = True

        # determine the success of the activity
        self.statuses["activity"] = self.statuses.get("generate")

        # send email only if new XML files were generated
        if self.statuses.get("generate") and new_meca_version_dois:
            self.logger.info("%s, sending admin email" % self.name)
            self.statuses["email"] = self.send_admin_email(new_meca_version_dois)
        else:
            self.logger.info("%s, no new DOI versions found" % self.name)

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def send_admin_email(self, new_meca_version_dois):
        "after do_activity is finished, send emails to admin with the status"
        datetime_string = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        activity_status_text = utils.get_activity_status_text(
            self.statuses.get("activity")
        )

        body = email_provider.get_email_body_head(
            self.name, activity_status_text, self.statuses
        )

        # Report on new MECA files
        if len(new_meca_version_dois) > 0:
            body += "\nVersion DOI with MECA file to ingest:\n"
            for version_doi in new_meca_version_dois:
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
            new_meca_version_dois,
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


RUN_FOLDER_PREFIX = "run_"


def date_from_run_folder(folder_name):
    "parse a date from a run folder name"
    try:
        date_string = "-".join(folder_name.split("_")[1:4])
    except AttributeError as exception:
        raise AttributeError("No date data found in %s" % folder_name) from exception
    try:
        return datetime.strptime("%s +0000" % date_string, "%Y-%m-%d %z")
    except ValueError as exception:
        raise ValueError("Could not parse date from %s" % folder_name) from exception


def run_folder_names(storage, resource):
    "get list of previous run folders from the bucket"
    # separate the bucket name from the other object path data
    bucket_name, bucket_path_prefix = storage.s3_storage_objects(resource)

    # full list of objects for the S3 prefix
    s3_key_names = storage.list_resources(resource)

    # match folder names by their start value
    starts_with = "%s%s" % (bucket_path_prefix.lstrip("/"), RUN_FOLDER_PREFIX)

    # filter by folder names only
    # avoid any subfolders by splitting by the delimiter count
    delimiter_count = starts_with.count("/")
    folders = [
        "/".join(key_name.split("/")[0 : delimiter_count + 1])
        for key_name in s3_key_names
        if key_name.count("/") > delimiter_count
    ]

    # list of run folder names
    run_folder_paths = [
        folder_path
        for folder_path in folders
        if folder_path.startswith(starts_with)
        and folder_path.count("/") == delimiter_count
    ]
    # strip away subfolder names and extra delimiter
    return sorted(
        [folder_name.rstrip("/").rsplit("/", 1)[-1] for folder_name in run_folder_paths]
    )


def new_run_folder(storage, bucket_path):
    "get a next run folder name"

    # get latest run folder index
    run_folders = run_folder_names(storage, bucket_path)
    date_string = datetime.strftime(utils.get_current_datetime(), "%Y_%m_%d")

    run_folder_prefix = "%s%s" % (RUN_FOLDER_PREFIX, date_string)
    filtered_run_folders = [
        folder_name
        for folder_name in run_folders
        if folder_name.startswith(run_folder_prefix)
    ]

    if filtered_run_folders:
        latest_run_folder = filtered_run_folders[-1]
        latest_run_index = int(latest_run_folder.rsplit("_", 1)[-1])
    else:
        latest_run_index = 0

    # increment to get the next run folder name
    return "%s_%s" % (run_folder_prefix, str(latest_run_index + 1).zfill(4))


def previous_run_folder(storage, bucket_path, from_folder=None):
    "find name of the previous run folder, previous to from_folder if specified"
    run_folders = run_folder_names(storage, bucket_path)

    if not run_folders:
        return None
    index = None
    # compare by the date value in the folder names
    if from_folder:
        from_date = date_from_run_folder(from_folder)
    else:
        from_date = utils.get_current_datetime()
    for idx, run_folder_name in enumerate(run_folders):
        if run_folder_name == from_folder:
            index = idx - 1
            break
        run_folder_date = date_from_run_folder(run_folder_name)
        if run_folder_date <= from_date:
            index = idx

    return run_folders[index]
