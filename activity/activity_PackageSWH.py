import json
import zipfile
import os
import requests
from provider.execution_context import get_session
from provider import software_heritage, utils
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_PackageSWH(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_PackageSWH, self).__init__(
            settings, logger, conn, token, activity_task
        )

        self.name = "PackageSWH"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download ERA article ZIP, verify contents, rename it for "
            "Software Heritage, and upload to bucket"
        )
        self.logger = logger

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        self.bucket_folder = "software_heritage/run"

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        run = data["run"]
        session = get_session(self.settings, data, run)
        article_id = session.get_value("article_id")

        storage = storage_context(self.settings)

        input_file = session.get_value("input_file")
        self.logger.info("Input file %s" % input_file)

        version = session.get_value("version")

        try:
            # download zip to temp folder
            file_name = software_heritage.FILE_NAME_FORMAT % (
                utils.pad_msid(article_id),
                version,
            )
            to_file = os.path.join(self.directories.get("INPUT_DIR"), file_name)
            local_zip_file = download_file(input_file, to_file, self.logger)
            self.logger.info("%s downloaded to %s" % (input_file, local_zip_file))
        except Exception:
            self.logger.exception("Exception raised downloading %s" % input_file)
            return self.ACTIVITY_PERMANENT_FAILURE

        # unzip the file to verify
        try:
            with zipfile.ZipFile(local_zip_file):
                self.logger.info("Zip file %s was opened successfully" % local_zip_file)
        except zipfile.BadZipFile:
            self.logger.exception("Exception when opening zip file %s" % local_zip_file)
            return self.ACTIVITY_PERMANENT_FAILURE

        # save zip file to S3
        try:
            resource_path = "/".join(
                [
                    self.settings.bot_bucket,
                    self.bucket_folder,
                    run,
                    file_name,
                ]
            )
            resource_dest = "%s://%s" % (
                self.settings.storage_provider,
                resource_path,
            )
            storage.set_resource_from_filename(resource_dest, local_zip_file)
            self.logger.info(
                "File %s saved to bucket resource %s" % (local_zip_file, resource_dest)
            )
        except Exception:
            self.logger.exception(
                "Exception raised saving %s to bucket resource %s"
                % (local_zip_file, resource_dest)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # save S3 location in session
        session.store_value("bucket_resource", resource_path)

        # clean temporary directory
        self.clean_tmp_dir()

        # return success
        return self.ACTIVITY_SUCCESS


def download_file(from_path, to_file, logger):
    request = requests.get(from_path)
    if request.status_code == 200:
        with open(to_file, "wb") as open_file:
            open_file.write(request.content)
        return to_file
    raise RuntimeError(
        "GET request returned a %s status code for %s"
        % (request.status_code, from_path)
    )
