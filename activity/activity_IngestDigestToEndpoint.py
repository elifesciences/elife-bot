import os
import json
from digestparser import json_output
from provider.storage_provider import storage_context
from provider.execution_context import get_session
import provider.digest_provider as digest_provider
import provider.lax_provider as lax_provider
from .activity import Activity


"""
activity_IngestDigestToEndpoint.py activity
"""


class activity_IngestDigestToEndpoint(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_IngestDigestToEndpoint, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "IngestDigestToEndpoint"
        self.pretty_name = "Ingest Digest to API endpoint"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = ("Send Digest JSON to an API endpoint," +
                            " to be run when a research article is ingested")

        # Local directory settings
        self.temp_dir = os.path.join(self.get_tmp_dir(), "tmp_dir")
        self.input_dir = os.path.join(self.get_tmp_dir(), "input_dir")

        # Create output directories
        self.create_activity_directories()

        # Track the success of some steps
        self.statuses = {
            "approve": None,
            "download": None,
            "generate": None,
            "ingest": None
        }

        # Digest JSON content
        self.digest_content = None

        # Load the config
        self.digest_config = digest_provider.digest_config(
            self.settings.digest_config_section,
            self.settings.digest_config_file)

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))
        success, run, session, article_id, version = self.session_data(data)

        # get session data
        if success is not True:
            self.logger.error("Failed to parse session data in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE
        # emit start message
        success = self.emit_start_message(article_id, version, run)
        if success is not True:
            self.logger.error("Failed to emit a start message in %s" % self.pretty_name)
            return self.ACTIVITY_PERMANENT_FAILURE

        # Wrap in an exception during testing phase
        try:
            # Approve for ingestion
            self.statuses["approve"] = self.approve(
                article_id, session.get_value("status"), version, session.get_value("run_type"))
            if self.statuses.get("approve") is not True:
                self.logger.info(
                    "Digest for article %s was not approved for ingestion" % article_id)
                return self.ACTIVITY_SUCCESS

            # check if there is a digest docx in the bucket for this article
            docx_file_exists = self.docx_exists_in_s3(article_id, self.settings.bot_bucket)
            if docx_file_exists is not True:
                self.logger.info(
                    "Digest docx file does not exist in S3 for article %s" % article_id)
                return self.ACTIVITY_SUCCESS

            # Download digest from the S3 outbox
            docx_file = self.download_docx_from_s3(
                article_id, self.settings.bot_bucket, self.input_dir)
            if docx_file:
                self.statuses["download"] = True
            if self.statuses.get("download") is not True:
                self.logger.info("Unable to download digest file %s for article %s" %
                                 (docx_file, article_id))
                return self.ACTIVITY_PERMANENT_FAILURE
            # find the image file name
            image_file = self.image_file_name_from_s3(
                article_id, self.settings.bot_bucket)

            # download jats file
            jats_file = self.download_jats(session.get_value("expanded_folder"))
            # related article data
            related = related_from_lax(article_id, version, self.settings, self.logger)
            # generate the digest content
            self.digest_content = self.digest_json(docx_file, jats_file, image_file, related)
            if self.digest_content:
                self.statuses["generate"] = True
            if self.statuses.get("generate") is not True:
                self.logger.info(
                    ("Unable to generate Digest content for docx_file %s, " +
                     "jats_file %s, image_file %s") %
                    (docx_file, jats_file, image_file))
                # for now return success to not impede the article ingest workflow
                return self.ACTIVITY_SUCCESS

            # get existing digest data
            digest_id = self.digest_content.get("id")
            existing_digest_json = digest_provider.get_digest(digest_id, self.settings)
            if not existing_digest_json:
                self.logger.info(
                    "Did not get existing digest json from the endpoint for digest_id %s" %
                    str(digest_id))
            self.digest_content = sync_json(self.digest_content, existing_digest_json)
            # set the stage attribute if missing
            set_stage(self.digest_content)
            self.logger.info("Digest stage value %s" % str(self.digest_content.get("stage")))

            self.statuses["ingest"] = self.put_digest_to_endpoint(
                digest_id, self.digest_content, self.settings)

        except Exception as exception:
            self.logger.exception("Exception raised in do_activity. Details: %s" % str(exception))

        self.emit_end_message(article_id, version, run)

        return self.ACTIVITY_SUCCESS

    def session_data(self, data):
        "get session data and return basic values"
        run = None
        session = None
        version = None
        article_id = None
        success = None
        try:
            run = data["run"]
            session = get_session(self.settings, data, run)
            version = session.get_value("version")
            article_id = session.get_value("article_id")
            success = True
        except (TypeError, KeyError) as exception:
            self.logger.exception("Exception when getting the session for Starting ingest digest " +
                                  " to endpoint. Details: %s" % str(exception))
        return success, run, session, article_id, version

    def emit_message(self, article_id, version, run, status, message):
        "emit message to the queue"
        try:
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, status, message)
            return True
        except Exception as exception:
            self.logger.exception("Exception emitting %s message. Details: %s" %
                                  (str(status), str(exception)))

    def emit_start_message(self, article_id, version, run):
        "emit the start message to the queue"
        return self.emit_message(
            article_id, version, run, "start",
            "Starting ingest digest to endpoint for " + str(article_id))

    def emit_end_message(self, article_id, version, run):
        "emit the end message to the queue"
        return self.emit_message(
            article_id, version, run, "end",
            "Finished ingest digest to endpoint for " + str(article_id))

    def emit_error_message(self, article_id, version, run, message):
        "emit an error message to the queue"
        return self.emit_message(
            article_id, version, run, "error", message)

    def approve(self, article_id, status, version, run_type):
        "should we ingest based on some basic attributes"
        approve_status = True

        # check by status
        return_status = approve_by_status(self.logger, article_id, status)
        if return_status is False:
            approve_status = return_status

        # check silent corrections and consider the first vor version
        run_type_status = approve_by_run_type(
            self.settings, self.logger, article_id, run_type, version)
        first_vor_status = approve_by_first_vor(self.settings, self.logger, article_id, version, status)
        if first_vor_status is False and run_type != "silent-correction":
            # not the first vor and not a silent correction, do not approve
            approve_status = False
        elif run_type_status is False:
            # otherwise depend on the silent correction run_type logic
            approve_status = False
 
        return approve_status

    def outbox_resource_path(self, article_id, bucket_name):
        "storage resource path for the outbox"
        return digest_provider.outbox_resource_path(
            self.settings.storage_provider, article_id, bucket_name)

    def docx_resource_origin(self, article_id, bucket_name):
        "the resource_origin of the docx file in the storage context"
        resource_path = self.outbox_resource_path(article_id, bucket_name)
        return resource_path + "/" + digest_provider.docx_file_name(article_id)

    def docx_exists_in_s3(self, article_id, bucket_name):
        "check if a digest docx exists in the S3 outbox"
        resource_origin = self.docx_resource_origin(article_id, bucket_name)
        storage = storage_context(self.settings)
        try:
            return storage.resource_exists(resource_origin)
        except Exception as exception:
            self.logger.exception(
                "Exception checking if digest docx exists for article %s. Details: %s" %
                (str(article_id), str(exception)))

    def download_docx_from_s3(self, article_id, bucket_name, to_dir):
        "download the docx file from the S3 outbox"
        docx_file = None
        resource_origin = self.docx_resource_origin(article_id, bucket_name)
        storage = storage_context(self.settings)
        try:
            docx_file = digest_provider.download_digest(
                storage, digest_provider.docx_file_name(article_id), resource_origin, to_dir)
        except Exception as exception:
            self.logger.exception(
                "Exception downloading docx for article %s. Details: %s" %
                (str(article_id), str(exception)))
        return docx_file

    def image_file_name_from_s3(self, article_id, bucket_name):
        "image file in the outbox is the non .docx file"
        image_file_name = None
        resource_path = self.outbox_resource_path(article_id, bucket_name)
        storage = storage_context(self.settings)
        object_list = storage.list_resources(resource_path)
        if object_list:
            for name in object_list:
                if not name.endswith(".docx"):
                    image_file_name = name.split("/")[-1]
        return image_file_name

    def download_jats(self, expanded_folder_name):
        "download the jats file from the expanded folder on S3"
        jats_file = None
        expanded_bucket_name = (self.settings.publishing_buckets_prefix
                                + self.settings.expanded_bucket)
        try:
            jats_file = download_article_xml(
                self.settings, self.temp_dir, expanded_folder_name, expanded_bucket_name)
        except Exception as exception:
            self.logger.exception(
                "Exception downloading jats from from expanded folder %s. Details: %s" %
                (str(expanded_folder_name), str(exception)))
        return jats_file

    def digest_json(self, docx_file, jats_file=None, image_file=None, related=None):
        "generate the digest json content from the docx file and other data"
        json_content = None
        try:
            json_content = json_output.build_json(docx_file, self.temp_dir, self.digest_config,
                                                  jats_file, image_file, related)
        except Exception as exception:
            self.logger.exception(
                "Exception generating digest json for docx_file %s. Details: %s" %
                (str(docx_file), str(exception)))
        return json_content

    def put_digest_to_endpoint(self, digest_id, digest_content, settings):
        "handle issuing the PUT to the digest endpoint"
        put_status = None
        try:
            digest_provider.put_digest(digest_id, digest_content, settings)
            put_status = True
        except Exception as exception:
            self.logger.exception(
                "Exception issuing PUT to the digest endpoint for digest_id %s. Details: %s" %
                (str(digest_id), str(exception)))
        return put_status

    def create_activity_directories(self):
        """
        Create the directories in the activity tmp_dir
        """
        for dir_name in [self.temp_dir, self.input_dir]:
            try:
                os.mkdir(dir_name)
            except OSError:
                pass


def approve_by_status(logger, article_id, status):
    "determine approval status by article status value"
    approve_status = None
    # PoA do not ingest digests
    if status == "poa":
        approve_status = False
        message = ("\nNot ingesting digest for PoA article {article_id}".format(
            article_id=article_id
        ))
        logger.info(message)
    return approve_status


def approve_by_run_type(settings, logger, article_id, run_type, version):
    approve_status = None
    # VoR and is a silent correction, consult Lax for if it is not the highest version
    if run_type == "silent-correction":
        highest_version = lax_provider.article_highest_version(article_id, settings)
        try:
            if int(version) < int(highest_version):
                approve_status = False
                message = (
                    "\nNot ingesting digest for silent correction {article_id}" +
                    " version {version} is less than highest version {highest}").format(
                        article_id=article_id,
                        version=version,
                        highest=highest_version)
                logger.info(message)
        except TypeError as exception:
            approve_status = False
            message = (
                "\nException converting version to int for {article_id}, {exc}").format(
                    article_id=article_id,
                    exc=str(exception))
            logger.exception(message.lstrip())
    return approve_status


def approve_by_first_vor(settings, logger, article_id, version, status, auth=True):
    "check if it is not the first vor or not the highest version"
    approve_status = None
    first_vor = lax_provider.article_first_by_status(article_id, version, status, settings, auth)
    highest_version = lax_provider.article_highest_version(article_id, settings, auth)
    if not first_vor:
        approve_status = False
    elif first_vor and version and highest_version and int(version) < int(highest_version):
        approve_status = False
    return approve_status


def download_article_xml(settings, to_dir, bucket_folder, bucket_name, version=None):
    xml_file = lax_provider.get_xml_file_name(
        settings, bucket_folder, bucket_name, version)
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    orig_resource = storage_provider + bucket_name + "/" + bucket_folder
    # download the file
    article_xml_filename = xml_file.split("/")[-1]
    filename_plus_path = os.path.join(to_dir, article_xml_filename)
    with open(filename_plus_path, "wb") as open_file:
        storage_resource_origin = orig_resource + "/" + article_xml_filename
        storage.get_resource_to_file(storage_resource_origin, open_file)
        return filename_plus_path


def related_from_lax(article_id, version, settings, logger=None, auth=True):
    "get article json from Lax and return as a list of related data"
    related = None
    related_json = None
    try:
        related_json = lax_provider.article_snippet(article_id, version, settings, auth)
    except Exception as exception:
        logger.exception(
            "Exception in getting article snippet from Lax for article_id %s, version %s. Details: %s" %
            (str(article_id), str(version), str(exception)))
    if related_json:
        related = [related_json]
    return related


def sync_json(json_content, existing_digest_json):
    "update values in json_content with some from existing digest json if present"
    if not existing_digest_json:
        return json_content
    for attr in ["published", "stage"]:
        if existing_digest_json.get(attr):
            json_content[attr] = existing_digest_json.get(attr)
    return json_content


def set_stage(json_content):
    "set the stage attribute if missing"
    if "stage" not in json_content:
        json_content["stage"] = "preview"
