import os
import json
from S3utility.s3_notification_info import parse_activity_data
from provider.storage_provider import storage_context
from provider import download_helper, letterparser_provider
from activity.objects import Activity

"""
DepositDecisionLetterIngestAssets.py activity
"""


class activity_DepositDecisionLetterIngestAssets(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_DepositDecisionLetterIngestAssets, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "DepositDecisionLetterIngestAssets"
        self.pretty_name = "Deposit Decision Letter Ingest Assets"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Deposit Assets for a Decision Letter to the output bucket"

        # Track some values
        self.input_file = None
        self.articles = None
        self.asset_file_names = None
        self.dest_resource = None

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir")
        }

        # Track the success of some steps
        self.statuses = {
            "unzip": None,
            "build": None,
            "valid": None,
            "upload": None,
        }

        # Load the config
        self.letterparser_config = letterparser_provider.letterparser_config(self.settings)

    def do_activity(self, data=None):
        "do the work"
        self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # Create output directories
        self.make_activity_directories()

        # output bucket
        output_bucket_name = self.settings.decision_letter_output_bucket

        # parse the activity data
        real_filename, bucket_name, bucket_folder = parse_activity_data(data)

        # Download from S3
        self.input_file = download_helper.download_file_from_s3(
            self.settings, real_filename, bucket_name, bucket_folder,
            self.directories.get("INPUT_DIR"))

        # zip file to articles and assets
        self.articles, self.asset_file_names, statuses, error_messages = (
            letterparser_provider.process_zip(
                self.input_file,
                config=self.letterparser_config,
                temp_dir=self.directories.get("TEMP_DIR"),
                logger=self.logger))

        self.set_statuses(statuses)

        # check if there are any assets if not return True
        if not self.asset_file_names:
            self.logger.info("%s file %s has no assets to deposit" % (self.name, self.input_file))
            return self.ACTIVITY_SUCCESS

        # S3 bucket folder name
        manuscript = letterparser_provider.manuscript_from_articles(self.articles)
        bucket_folder_name = letterparser_provider.output_bucket_folder_name(
            self.settings, manuscript)

        self.logger.info(
            "%s asset file names from %s: %s" % (self.name, self.input_file, self.asset_file_names))

        # deposit assets to the bucket
        try:
            self.deposit_assets_to_bucket(
                output_bucket_name, bucket_folder_name, self.asset_file_names)
        except:
            self.logger.exception('%s failed to upload an asset to the bucket' % self.name)
            return self.ACTIVITY_PERMANENT_FAILURE

        self.statuses['upload'] = True
        self.log_statuses(self.input_file)
        return self.ACTIVITY_SUCCESS

    def set_statuses(self, statuses):
        """copy statuses values to self.statuses"""
        for status, value in statuses.items():
            self.statuses[status] = value

    def log_statuses(self, input_file):
        "log the statuses value"
        self.logger.info(
            "%s for input_file %s statuses: %s" % (self.name, str(input_file), self.statuses))

    def asset_dest_resource(self, bucket_name, folder_name, asset_file_name):
        "concatenate the S3 bucket object path we copy the file to"
        file_name = asset_file_name.split(os.sep)[-1]
        storage_provider = self.settings.storage_provider + "://"
        dest_resource = storage_provider + bucket_name + "/" + folder_name + "/" + file_name
        return dest_resource

    def deposit_assets_to_bucket(self, output_bucket, bucket_folder_name, asset_file_names):
        "deposit the assets to the output bucket"
        for asset_file_name in asset_file_names:
            dest_resource = self.asset_dest_resource(
                output_bucket, bucket_folder_name, asset_file_name)
            storage = storage_context(self.settings)
            self.logger.info("Depositing asset %s to S3 key %s" % (asset_file_name, dest_resource))
            # set the bucket object resource from the local file
            storage.set_resource_from_filename(dest_resource, asset_file_name)
            self.logger.info("Deposited asset %s to S3" % asset_file_name)
