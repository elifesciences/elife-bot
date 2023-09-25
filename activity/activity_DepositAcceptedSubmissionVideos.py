import os
import json
import glob
import shutil
import zipfile
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner
from provider.cleaner import SettingsException
from provider.ftp import FTP
from activity.objects import AcceptedBaseActivity


FILE_NAME_PREFIX = "elife_videos_"

# session variable name to store the number of attempts
SESSION_ATTEMPT_COUNTER_NAME = "video_deposit_ftp_attempt_count"

MAX_ATTEMPTS = 3


class activity_DepositAcceptedSubmissionVideos(AcceptedBaseActivity):
    "DepositAcceptedSubmissionVideos activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DepositAcceptedSubmissionVideos, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DepositAcceptedSubmissionVideos"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Package video and XML into a zip file and deposit to a video service."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"generate": None, "zip": None, "deposit": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        expanded_folder, input_filename, article_id = self.read_session(session)

        deposit_videos = session.get_value("deposit_videos")

        self.logger.info(
            "%s, input_filename: %s, expanded_folder: %s"
            % (self.name, input_filename, expanded_folder)
        )

        # if there are no videos to deposit return True
        if not deposit_videos:
            self.logger.info(
                "%s, %s deposit_videos session value is %s, activity returning True"
                % (self.name, input_filename, deposit_videos)
            )
            return True

        # if there are insufficient deposit credentials return True
        settings_required = [
            "GLENCOE_FTP_URI",
            "GLENCOE_FTP_USERNAME",
            "GLENCOE_FTP_PASSWORD",
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

        # get a list of video files from the XML
        try:
            video_files = cleaner.video_file_list(xml_file_path)
            self.logger.info(
                "%s, %s video_files: %s" % (self.name, input_filename, video_files)
            )
        except ParseError:
            log_message = (
                "%s, XML ParseError exception parsing video file list from %s for file %s"
                % (
                    self.name,
                    xml_file_path,
                    input_filename,
                )
            )
            self.logger.exception(log_message)
            video_files = []

        # download video files from the bucket folder
        if video_files:
            cleaner.download_asset_files_from_bucket(
                storage,
                video_files,
                asset_file_name_map,
                self.directories.get("INPUT_DIR"),
                self.logger,
            )
            video_data = cleaner.video_data_from_files(video_files, article_id)

        # generate glencoe XML
        if video_files:
            glencoe_xml_file_path = self.generate_video_xml(
                input_filename, xml_file_path, video_data
            )
            self.statuses["generate"] = True

        # zip up the files and XML
        if self.statuses.get("generate"):
            self.create_video_zip(
                asset_file_name_map, input_filename, video_data, glencoe_xml_file_path
            )
            self.statuses["zip"] = True

        # FTP the zip file to Glencoe
        if self.statuses.get("zip"):

            try:
                self.statuses["deposit"] = self.ftp_to_endpoint(
                    self.directories.get("TEMP_DIR")
                )
                # set session variable for whether to check for Glencoe metadata
                session.store_value("annotate_videos", True)
            except Exception as exception:
                message = "%s, exception in ftp_to_endpoint sending file %s: %s" % (
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
                    "%s, ftp_to_endpoint attempts for file %s: %s"
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
                        "%s, ftp_to_endpoint attempts reached MAX_ATTEMPTS of %s for file %s"
                        % (self.name, MAX_ATTEMPTS, input_filename)
                    )
                    return True

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def generate_video_xml(self, input_filename, xml_file_path, video_data):
        "generate a JATS XML file containing video deposit metadata"
        glencoe_xml_file_name = "%s%s.xml" % (
            FILE_NAME_PREFIX,
            input_filename.rsplit(".", 1)[0],
        )
        xml_string = cleaner.glencoe_xml(xml_file_path, video_data)
        glencoe_xml_file_path = os.path.join(
            self.directories.get("TEMP_DIR"), glencoe_xml_file_name
        )
        self.logger.info(
            "%s, writing video XML for %s to %s"
            % (self.name, input_filename, glencoe_xml_file_path)
        )
        with open(glencoe_xml_file_path, "wb") as open_file:
            open_file.write(xml_string)
        return glencoe_xml_file_path

    def create_video_zip(
        self, asset_file_name_map, input_filename, video_data, glencoe_xml_file_path
    ):
        "create zip file containing video files and video XML"
        # map of asset key names
        asset_key_map = {key.rsplit("/", 1)[-1]: key for key in asset_file_name_map}
        # zip file name
        glencoe_zip_file_name = "%s%s" % (FILE_NAME_PREFIX, input_filename)
        glencoe_zip_file_path = os.path.join(
            self.directories.get("TEMP_DIR"), glencoe_zip_file_name
        )
        with zipfile.ZipFile(
            glencoe_zip_file_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True
        ) as open_zip:
            # add video files
            for video in video_data:
                video_asset_key = asset_key_map.get(video.get("video_filename"))
                video_file_path = asset_file_name_map.get(video_asset_key)
                self.logger.info(
                    "%s, adding video file %s to zip file %s"
                    % (self.name, video_file_path, glencoe_zip_file_path)
                )
                arcname = video_file_path.rsplit(os.sep, 1)[-1]
                open_zip.write(video_file_path, arcname)
            # add XML file
            self.logger.info(
                "%s, adding video XML file %s to zip file %s"
                % (self.name, glencoe_xml_file_path, glencoe_zip_file_path)
            )
            arcname = glencoe_xml_file_path.rsplit(os.sep, 1)[-1]
            open_zip.write(glencoe_xml_file_path, arcname)

    def ftp_to_endpoint(self, from_dir, file_type="/*.zip", passive=True):
        """
        FTP files to endpoint
        as specified by the file_type to use in the glob
        e.g. "/*.zip"
        """
        try:
            ftp_provider = FTP(self.logger)
            ftp_instance = ftp_provider.ftp_connect(
                uri=self.settings.GLENCOE_FTP_URI,
                username=self.settings.GLENCOE_FTP_USERNAME,
                password=self.settings.GLENCOE_FTP_PASSWORD,
                passive=passive,
            )
        except Exception as exception:
            self.logger.exception("Exception connecting to FTP server: %s" % exception)
            raise

        # collect the list of files
        zipfiles = glob.glob(from_dir + file_type)

        try:
            # transfer them by FTP to the endpoint
            ftp_provider.ftp_to_endpoint(
                ftp_instance=ftp_instance,
                uploadfiles=zipfiles,
                sub_dir_list=[self.settings.GLENCOE_FTP_CWD],
            )
        except Exception as exception:
            self.logger.exception(
                "Exception in transfer of files by FTP: %s" % exception
            )
            ftp_provider.ftp_disconnect(ftp_instance)
            raise

        try:
            # disconnect the FTP connection
            ftp_provider.ftp_disconnect(ftp_instance)
        except Exception as exception:
            self.logger.exception(
                "Exception disconnecting from FTP server: %s" % exception
            )
            raise

        return True
