import os
import json
from S3utility.s3_notification_info import parse_activity_data
from provider import download_helper, letterparser_provider
from provider.storage_provider import storage_context
from provider.execution_context import get_session
from activity.objects import Activity


class activity_GenerateDecisionLetterJATS(Activity):
    "ValidateDecisionLetter activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_GenerateDecisionLetterJATS, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "GenerateDecisionLetterJATS"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "From decision letter zip file, convert its docx file to JATS XML"
        )

        # Track some values
        self.input_file = None
        self.articles = None
        self.xml_string = None
        self.xml_bucket_resource = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "generate": None,
            "output": None,
            "upload": None,
        }

        # Load the config
        self.letterparser_config = letterparser_provider.letterparser_config(
            self.settings
        )

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # session
        run = data["run"]
        session = get_session(self.settings, data, run)

        # output bucket
        output_bucket_name = self.settings.decision_letter_output_bucket

        # parse the activity data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )

        # part 1 zip file to articles and assets
        (
            self.articles,
            asset_file_names,
            statuses,
            error_messages,
        ) = letterparser_provider.process_zip(
            self.input_file,
            config=self.letterparser_config,
            temp_dir=self.directories.get("TEMP_DIR"),
            logger=self.logger,
        )
        # part 2 articles to XML
        self.xml_string, statuses = letterparser_provider.process_articles_to_xml(
            self.articles, self.directories.get("TEMP_DIR"), self.logger
        )

        self.set_statuses(statuses)

        # Populate folder and file names
        manuscript = letterparser_provider.manuscript_from_articles(self.articles)
        bucket_folder_name = letterparser_provider.output_bucket_folder_name(
            self.settings, manuscript
        )
        xml_file_name = letterparser_provider.output_xml_file_name(
            self.settings, manuscript
        )

        # Upload XML to bucket
        self.xml_bucket_resource = download_helper.file_resource_origin(
            self.settings.storage_provider,
            xml_file_name,
            output_bucket_name,
            bucket_folder_name,
        )
        storage = storage_context(self.settings)
        try:
            storage.set_resource_from_string(self.xml_bucket_resource, self.xml_string)
            self.statuses["upload"] = True
        except:
            self.log_statuses(self.input_file)
            self.logger.exception(
                "An error occurred uploading XML in %s" % self.pretty_name
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # Save values to the session
        session.store_value("bucket_folder_name", bucket_folder_name)
        session.store_value("xml_file_name", xml_file_name)

        self.log_statuses(self.input_file)
        return True

    def set_statuses(self, statuses):
        """copy statuses values to self.statuses"""
        for status, value in statuses.items():
            self.statuses[status] = value

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )
