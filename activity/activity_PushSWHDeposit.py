import json
import os
from provider.execution_context import get_session
from provider import software_heritage, utils
from provider.storage_provider import storage_context
from activity.objects import Activity

DESCRIPTION_PATTERN = 'ERA complement for "%s", %s'


class activity_PushSWHDeposit(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PushSWHDeposit, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "PushSWHDeposit"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Push Software Heritage deposit file to the API endpoint"
        self.logger = logger

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        run = data["run"]
        session = get_session(self.settings, data, run)
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        input_file = session.get_value("input_file")
        bucket_resource = session.get_value("bucket_resource")
        bucket_metadata_resource = session.get_value("bucket_metadata_resource")
        self.logger.info(
            (
                "%s activity session data: article_id: %s, version: %s, input_file: %s, "
                "bucket_resource: %s, bucket_metadata_resource: %s"
            )
            % (
                self.name,
                article_id,
                version,
                input_file,
                bucket_resource,
                bucket_metadata_resource,
            )
        )

        # Push the deposit to Software Heritage
        if not self.settings.software_heritage_deposit_endpoint:
            # if no endpoint is specified then return failure before attempting HTTP request
            self.logger.info(
                "%s, software_heritage_deposit_endpoint setting is empty or missing" % self.name
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # Download the zip file and metadata XML from the bucket folder
        zip_file_path = download_bucket_resource(
            self.settings,
            bucket_resource,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )
        atom_file_path = download_bucket_resource(
            self.settings,
            bucket_metadata_resource,
            self.directories.get("INPUT_DIR"),
            self.logger,
        )

        url = "%s/%s/" % (
            self.settings.software_heritage_deposit_endpoint,
            self.settings.software_heritage_collection_name,
        )

        try:
            response = software_heritage.swh_post_request(
                url,
                self.settings.software_heritage_auth_user,
                self.settings.software_heritage_auth_pass,
                zip_file_path,
                atom_file_path,
                logger=self.logger,
            )
            self.logger.info(
                "%s, finished post request to %s, zip_file_path %s, atom_file_path %s"
                % (self.name, url, zip_file_path, atom_file_path)
            )
        except Exception as exception:
            self.logger.exception(
                "Exception in %s posting to SWH API endpoint, article_id %s: %s"
                % (self.name, article_id, str(exception)),
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # clean temporary directory

        # do not deleted files from the temp folder for now so they can be inspected
        # self.clean_tmp_dir()

        # return success
        return self.ACTIVITY_SUCCESS


def download_bucket_resource(settings, storage_resource, to_dir, logger):
    storage = storage_context(settings)
    storage_provider = settings.storage_provider + "://"
    storage_resource_origin = "%s%s/%s" % (
        storage_provider,
        settings.bot_bucket,
        storage_resource,
    )
    file_name = storage_resource_origin.split("/")[-1]
    file_path = os.path.join(to_dir, file_name)
    with open(file_path, "wb") as open_file:
        logger.info("Downloading %s to %s", (storage_resource_origin, file_path))
        storage.get_resource_to_file(storage_resource_origin, open_file)
    return file_path
