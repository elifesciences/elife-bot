import json
import os
from xml.parsers.expat import ExpatError
from elifecleaner import parse, zip_lib
from elifetools import xmlio
from S3utility.s3_notification_info import parse_activity_data
from provider import article_processing, download_helper, outbox_provider
from activity.objects import Activity


class activity_ScheduleCrossrefPendingPublication(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ScheduleCrossrefPendingPublication, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "ScheduleCrossrefPendingPublication"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Queue the article XML for depositing as a "
            "pending publication DOI to Crossref."
        )
        self.logger = logger
        self.pretty_name = "Schedule Crossref Pending Publication"

        # Track some values
        self.input_file = None

        # For copying to S3 bucket outbox
        self.crossref_outbox_folder = "crossref_pending_publication/outbox/"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):

        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # data is an S3 bucket notification message for an accepted submission zip file
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)
        self.logger.info(
            "%s, real_filename: %s, bucket_name: %s, bucket_folder: %s"
            % (self.name, real_filename, bucket_name, bucket_folder)
        )

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings,
            real_filename,
            bucket_name,
            bucket_folder,
            self.directories.get("INPUT_DIR"),
        )

        self.logger.info("%s, downloaded file to %s" % (self.name, self.input_file))

        # unzip the file, repair the XML, and save to disk
        asset_file_name_map = zip_lib.unzip_zip(
            self.input_file, self.directories.get("TEMP_DIR")
        )
        xml_asset_details = parse.article_xml_asset(asset_file_name_map)
        input_xml_path = xml_asset_details[1]
        root = parse.parse_article_xml(input_xml_path)

        # convert ElementTree root to an XML string
        try:
            xml_string = xmlio.output_root(root, None, None)
        except ExpatError:
            log_message = (
                "%s, XML ExpatError exception in xmlio.output_root for file %s"
                % (self.name, input_xml_path)
            )
            self.logger.exception(log_message)
            return self.ACTIVITY_PERMANENT_FAILURE

        # todo!! save to disk
        output_file_name = article_processing.file_name_from_name(input_xml_path)
        output_file_path = os.path.join(
            self.directories.get("TEMP_DIR"), output_file_name
        )
        with open(output_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)

        # upload to the outbox folder
        outbox_provider.upload_files_to_s3_folder(
            self.settings,
            self.settings.poa_packaging_bucket,
            self.crossref_outbox_folder,
            [output_file_path],
        )

        # Clean up disk
        self.clean_tmp_dir()

        return True
