import os
import json
from elifecleaner.transform import ArticleZipFile
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner
from activity.objects import AcceptedBaseActivity


class activity_AcceptedSubmissionPeerReviewFigs(AcceptedBaseActivity):
    "AcceptedSubmissionPeerReviewFigs activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionPeerReviewFigs, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionPeerReviewFigs"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Transform certain peer review inline graphic image content into "
            "fig tags and images."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"hrefs": None, "modify_xml": None, "rename_files": None}

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

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        expanded_folder, input_filename, article_id = self.read_session(session)

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # search XML file for graphic tags
        inline_graphic_tags = cleaner.inline_graphic_tags(xml_file_path)
        if not inline_graphic_tags:
            self.logger.info(
                "%s, no inline-graphic tags in %s" % (self.name, input_filename)
            )
            self.end_cleaner_log(session)
            return True

        self.statuses["hrefs"] = True

        xml_root = cleaner.parse_article_xml(xml_file_path)

        file_transformations = []
        for sub_article_index, sub_article_root in enumerate(
            xml_root.iterfind("./sub-article")
        ):
            # list of old file names
            previous_hrefs = cleaner.inline_graphic_hrefs(
                sub_article_root, input_filename
            )
            cleaner.transform_fig(sub_article_root, input_filename)
            # list of new file names
            current_hrefs = cleaner.graphic_hrefs(sub_article_root, input_filename)
            # add to file_transformations
            self.logger.info(
                "%s, sub-article %s previous_hrefs: %s"
                % (self.name, sub_article_index, previous_hrefs)
            )
            self.logger.info(
                "%s, sub-article %s current_hrefs: %s"
                % (self.name, sub_article_index, current_hrefs)
            )
            for index, previous_href in enumerate(previous_hrefs):
                current_href = current_hrefs[index]
                from_file = ArticleZipFile(previous_href)
                to_file = ArticleZipFile(current_href)
                file_transformations.append((from_file, to_file))
        self.logger.info(
            "%s, total file_transformations: %s"
            % (self.name, len(file_transformations))
        )
        self.logger.info(
            "%s, file_transformations: %s" % (self.name, file_transformations)
        )

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

        # rewrite the XML file with the renamed files
        if file_transformations:
            self.statuses["modify_xml"] = self.rewrite_file_tags(
                xml_file_path, file_transformations, input_filename
            )

        # rename the files in the expanded folder
        if self.statuses["modify_xml"]:
            try:
                self.statuses["rename_files"] = self.rename_expanded_folder_files(
                    asset_file_name_map, expanded_folder, file_transformations, storage
                )
            except RuntimeError as exception:
                log_message = "%s, exception in rewrite_file_tags for file %s" % (
                    self.name,
                    input_filename,
                )
                self.logger.exception(log_message)
                return self.ACTIVITY_PERMANENT_FAILURE

        # upload the XML to the bucket
        self.upload_xml_file_to_bucket(asset_file_name_map, expanded_folder, storage)

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True
