import os
import glob
import json
from provider import outbox_provider, preprint, meca
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_GeneratePreprintPDF(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_GeneratePreprintPDF, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "GeneratePreprintPDF"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Generate a preprint PDF using a service endpoint"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.statuses = {}

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "generate_preprint_pdf_api_endpoint"):
            self.logger.info(
                "%s, generate_preprint_pdf_api_endpoint in settings is missing, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.generate_preprint_pdf_api_endpoint:
            self.logger.info(
                "%s, generate_preprint_pdf_api_endpoint in settings is blank, skipping"
                % self.name
            )
            return self.ACTIVITY_SUCCESS

        self.make_activity_directories()

        # load session
        run = data["run"]
        session = get_session(self.settings, data, run)
        # load session data
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        article_xml_path = session.get_value("article_xml_path")
        expanded_folder = session.get_value("expanded_folder")

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # local path to the article XML file
        xml_file_path = os.path.join(
            self.directories.get("INPUT_DIR"), article_xml_path
        )  # local path to the article XML file

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        orig_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # download XML from the bucket folder
        storage_resource_origin = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        self.statuses["download"] = True

        # post to endpoint the XML data
        endpoint_url = self.settings.generate_preprint_pdf_api_endpoint
        self.logger.info("%s, endpoint url %s" % (self.name, endpoint_url))
        try:
            response_content = meca.post_to_preprint_pdf_endpoint(
                xml_file_path,
                endpoint_url,
                user_agent=getattr(self.settings, "user_agent", None),
                caller_name=self.name,
                logger=self.logger,
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception raised posting to endpoint %s: %s"
                % (self.name, endpoint_url, str(exception))
            )
            response_content = None

        if not response_content:
            self.logger.info(
                "%s, for article_id %s version %s got no response_content"
                % (self.name, article_id, version)
            )
            # return a success to ignore the blank result
            return self.ACTIVITY_SUCCESS
        else:
            self.logger.info(
                "%s, for article_id %s version %s response_content length %s"
                % (self.name, article_id, version, len(response_content))
            )

        # if successful response, save the PDF file to disk
        try:
            pdf_file_name = preprint.generate_new_pdf_href(article_id, version, None)
            self.logger.info(
                "%s, for article_id %s version %s pdf_file_name: %s"
                % (self.name, article_id, version, pdf_file_name)
            )
            pdf_file_path = os.path.join(
                self.directories.get("TEMP_DIR"), pdf_file_name
            )
            self.logger.info(
                "%s, for article_id %s version %s writing response content to %s"
                % (self.name, article_id, version, pdf_file_path)
            )
            with open(pdf_file_path, "wb") as open_file:
                open_file.write(response_content)
        except Exception as exception:
            self.logger.exception(
                "%s, for article_id %s version %s exception raised saving PDF to disk: %s"
                % (self.name, article_id, version, str(exception))
            )
            # return a success if an exception is raised
            return self.ACTIVITY_SUCCESS

        # temporarily, upload the PDF file to S3
        try:
            bucket_name = self.settings.poa_packaging_bucket
            upload_file_names = glob.glob(
                os.path.join(self.directories.get("TEMP_DIR"), "*.pdf")
            )
            upload_file_to_folder = "_sample_preprint_pdf/"
            outbox_provider.upload_files_to_s3_folder(
                self.settings,
                bucket_name,
                upload_file_to_folder,
                upload_file_names,
            )
        except Exception as exception:
            self.logger.exception(
                "%s, for article_id %s version %s exception raised uploading PDF to S3: %s"
                % (self.name, article_id, version, str(exception))
            )
            # return a success if an exception is raised
            return self.ACTIVITY_SUCCESS

        # todo ! save S3 PDF file path into the session
        # session.store_value("pdf_url_TODO_NEW_VALUE_NAME_HERE", pdf_url)

        # todo ! use the PDF file

        return self.ACTIVITY_SUCCESS
