import os
import json
from xml.etree.ElementTree import ParseError
from provider import cleaner, glencoe_check
from provider.cleaner import SettingsException
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import AcceptedBaseActivity


# session variable name to store the number of attempts
SESSION_ATTEMPT_COUNTER_NAME = "video_metadata_attempt_count"

MAX_ATTEMPTS = 12


class activity_AnnotateAcceptedSubmissionVideos(AcceptedBaseActivity):
    "AnnotateAcceptedSubmissionVideos activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AnnotateAcceptedSubmissionVideos, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AnnotateAcceptedSubmissionVideos"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Get video metadata from the API endpoint and"
            " add metadata to accepted submission XML."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"get": None, "annotate": None, "upload_xml": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        annotate_videos = session.get_value("annotate_videos")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # if there are no videos to annotate return True
        if not annotate_videos:
            self.logger.info(
                "%s, %s annotate_videos session value is %s, activity returning True"
                % (self.name, input_filename, annotate_videos)
            )
            return True

        # if there are insufficient credentials return True
        settings_required = [
            "video_url",
        ]
        try:
            cleaner.verify_settings(
                self.settings, settings_required, self.name, input_filename
            )
        except SettingsException as exception:
            self.logger.exception(str(exception))
            return True

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # get metadata from video service endpoint
        try:
            gc_data = glencoe_check.metadata(
                glencoe_check.check_msid(article_id), self.settings
            )
            self.logger.info("gc_data: %s" % json.dumps(gc_data, indent=4))
            self.statuses["get"] = True
        except Exception as exception:
            # handle Glencoe API responses
            message = "%s, exception in glencoe_check metadata for file %s: %s" % (
                self.name,
                input_filename,
                exception,
            )
            # log when an exception is raised
            self.logger.exception(message)
            # count the number of attempts
            if not session.get_value(SESSION_ATTEMPT_COUNTER_NAME):
                session.store_value(SESSION_ATTEMPT_COUNTER_NAME, 1)
            else:
                # increment
                session.store_value(
                    SESSION_ATTEMPT_COUNTER_NAME,
                    int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) + 1,
                )
            self.logger.info(
                "%s, glencoe_check metadata attempts for file %s: %s"
                % (
                    self.name,
                    input_filename,
                    session.get_value(SESSION_ATTEMPT_COUNTER_NAME),
                )
            )
            self.log_statuses(input_filename)
            # Clean up disk
            self.clean_tmp_dir()
            if int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) < MAX_ATTEMPTS:
                # return a temporary failure
                return self.ACTIVITY_TEMPORARY_FAILURE
            if int(session.get_value(SESSION_ATTEMPT_COUNTER_NAME)) >= MAX_ATTEMPTS:
                # return success after the maximum number of attempts to continue the workflow
                self.logger.info(
                    "%s, glencoe_check metadata attempts reached MAX_ATTEMPTS of %s for file %s"
                    % (self.name, MAX_ATTEMPTS, input_filename)
                )
                return True

        # parse XML
        try:
            root = cleaner.parse_article_xml(xml_file_path)
            video_files = cleaner.video_file_list(xml_file_path)
            self.logger.info("%s, %s XML root parsed" % (self.name, input_filename))
            generated_video_data = cleaner.video_data_from_files(
                video_files, article_id
            )
        except ParseError:
            log_message = "%s, XML ParseError exception parsing XML %s for file %s" % (
                self.name,
                xml_file_path,
                input_filename,
            )
            self.logger.exception(log_message)
            root = None

            generated_video_data = []

        if root:
            try:
                # for each video_id, get the glencoe video metadata
                annotate_xml(
                    root, xml_file_path, generated_video_data, gc_data, input_filename
                )
                self.statuses["annotate"] = True
            except:
                log_message = "%s, exception in annotate_xml %s for file %s" % (
                    self.name,
                    xml_file_path,
                    input_filename,
                )
                self.logger.exception(log_message)

        # upload the modified XML file to the expanded folder
        if self.statuses.get("annotate"):
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True


def annotate_xml(root, xml_file_path, generated_video_data, gc_data, input_filename):
    # for each video_id, get the glencoe video metadata
    for video_data in generated_video_data:
        video_id = video_data.get("video_id")
        gc_video_data = gc_data.get(video_id)
        video_data["glencoe_mp4"] = gc_video_data.get("mp4_href")
        video_data["glencoe_jpg"] = gc_video_data.get("jpg_href")
    # modify the file tag attributes
    file_name_data_map = {
        video_data.get("upload_file_nm"): video_data
        for video_data in generated_video_data
    }
    for file_tag in root.findall("./front/article-meta/files/file"):
        for file_nm_tag in file_tag.findall("./upload_file_nm"):
            if file_nm_tag.text in file_name_data_map:
                video_data = file_name_data_map.get(file_nm_tag.text)
                file_tag.set("id", video_data.get("video_id"))
                file_tag.set("glencoe-mp4", video_data.get("glencoe_mp4"))
                file_tag.set("glencoe-jpg", video_data.get("glencoe_jpg"))
    # write the modified XML to disk
    cleaner.write_xml_file(root, xml_file_path, input_filename)
