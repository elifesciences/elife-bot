import os
import json
import shutil
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, utils
from activity.objects import Activity


REPAIR_XML = False


class activity_AcceptedSubmissionPeerReviews(Activity):
    "AcceptedSubmissionPeerReviews activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionPeerReviews, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionPeerReviews"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download peer review material and add it to the accepted submission XML."
        )

        # Track some values
        self.input_file = None
        self.activity_log_file = "cleaner.log"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"docmap_string": None, "xml_root": None, "upload_xml": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        run = data["run"]
        session = get_session(self.settings, data, run)

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        log_file_path = os.path.join(
            self.get_tmp_dir(), self.activity_log_file
        )  # log file for this activity only
        cleaner_log_handers = cleaner.configure_activity_log_handlers(log_file_path)

        expanded_folder = session.get_value("expanded_folder")
        input_filename = session.get_value("input_filename")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # if the article is not PRC, return True
        prc_status = session.get_value("prc_status")
        if not prc_status:
            self.logger.info(
                "%s, %s prc_status session value is %s, activity returning True"
                % (self.name, input_filename, prc_status)
            )
            return True

        # get list of bucket objects from expanded folder
        asset_file_name_map = cleaner.bucket_asset_file_name_map(
            self.settings, self.settings.bot_bucket, expanded_folder
        )
        self.logger.info(
            "%s, asset_file_name_map: %s" % (self.name, asset_file_name_map)
        )

        # find S3 object for article XML and download it
        xml_file_path = cleaner.download_xml_file_from_bucket(
            self.settings,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # generate docmap URL
        docmap_url = cleaner.docmap_url(self.settings, session.get_value("article_id"))
        self.logger.info("%s, docmap_url: %s" % (self.name, docmap_url))

        # get docmap json
        self.logger.info(
            "%s, getting docmap_string for input_filename: %s"
            % (self.name, input_filename)
        )
        docmap_string = cleaner.get_docmap_by_account_id(
            docmap_url, self.settings.docmap_account_id
        )
        self.statuses["docmap_string"] = True

        # get sub-article data from docmap
        self.logger.info(
            "%s, generating xml_root including sub-article tags for input_filename: %s"
            % (self.name, input_filename)
        )
        terms_yaml = getattr(self.settings, "assessment_terms_yaml", None)
        xml_root = cleaner.add_sub_article_xml(docmap_string, xml_file_path, terms_yaml)
        self.statuses["xml_root"] = True

        # remove ext-link tag if it wraps an inline-graphic tag
        cleaner.clean_inline_graphic_tags(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

        # upload the XML to the bucket
        upload_key = cleaner.article_xml_asset(asset_file_name_map)[0]
        s3_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
            + "/"
            + upload_key
        )
        local_file_path = asset_file_name_map.get(upload_key)
        storage.set_resource_from_filename(s3_resource, local_file_path)
        self.logger.info(
            "%s, uploaded %s to S3 object: %s"
            % (self.name, local_file_path, s3_resource)
        )
        self.statuses["upload_xml"] = True

        # remove the log handlers
        for log_handler in cleaner_log_handers:
            cleaner.log_remove_handler(log_handler)

        # read the cleaner log contents
        with open(log_file_path, "r", encoding="utf8") as open_file:
            log_contents = open_file.read()

        # add the log_contents to the session variable
        cleaner_log = session.get_value("cleaner_log")
        if cleaner_log is None:
            cleaner_log = log_contents
        else:
            cleaner_log += log_contents
        session.store_value("cleaner_log", cleaner_log)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s"
            % (self.name, str(input_file), self.statuses)
        )

    def clean_tmp_dir(self):
        "custom cleaning of temp directory in order to retain some files for debugging purposes"
        keep_dirs = []
        for dir_name, dir_path in self.directories.items():
            if dir_name in keep_dirs or not os.path.exists(dir_path):
                continue
            shutil.rmtree(dir_path)
