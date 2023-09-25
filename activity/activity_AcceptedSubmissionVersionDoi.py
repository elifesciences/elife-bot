import os
import json
import shutil
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, utils
from activity.objects import AcceptedBaseActivity


class activity_AcceptedSubmissionVersionDoi(AcceptedBaseActivity):
    "AcceptedSubmissionVersionDoi activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionVersionDoi, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionVersionDoi"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Add a version DOI the accepted submission XML."

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

        session = get_session(self.settings, data, data["run"])

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        expanded_folder, input_filename, article_id = self.read_session(session)

        # if the article is not PRC, return True
        prc_status = session.get_value("prc_status")
        if not prc_status:
            self.logger.info(
                "%s, %s prc_status session value is %s, activity returning True"
                % (self.name, input_filename, prc_status)
            )
            return True

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # get docmap as a string
        docmap_string = self.get_docmap_string(article_id, input_filename)
        self.statuses["docmap_string"] = True

        # get latest version DOI from the docmap
        version_doi = cleaner.version_doi_from_docmap(docmap_string, input_filename)
        self.logger.info(
            "%s, %s version_doi: %s" % (self.name, input_filename, version_doi)
        )

        # tget the next version DOI value
        next_version_doi = cleaner.next_version_doi(version_doi, input_filename)
        self.logger.info(
            "%s, %s next_version_doi: %s"
            % (self.name, input_filename, next_version_doi)
        )

        # add log messages if an external href is not approved to download
        if not next_version_doi:
            cleaner.LOGGER.warning(
                "%s A version DOI was not added to the XML", input_filename
            )

        # add the article-id tag to the XML file
        if next_version_doi:
            xml_root = cleaner.parse_article_xml(xml_file_path)
            cleaner.add_version_doi(xml_root, next_version_doi, input_filename)

            self.statuses["xml_root"] = True

        if self.statuses.get("xml_root"):
            # write the XML root to disk
            cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

            # upload the XML to the bucket
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True
