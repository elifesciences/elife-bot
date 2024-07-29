import os
import json
import zipfile
from provider import article_processing, meca
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from activity.objects import Activity


class activity_OutputMeca(Activity):
    "OutputMeca activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_OutputMeca, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "OutputMeca"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download files from a MECA bucket folder, zip them, "
            "and copy to the MECA output bucket."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
            "OUTPUT_DIR": os.path.join(self.get_tmp_dir(), "output_dir"),
        }

        # Track the success of some steps
        self.statuses = {"download": None, "zip": None, "upload": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        # check for required settings
        if not hasattr(self.settings, "meca_bucket"):
            self.logger.info(
                "%s, meca_bucket in settings is missing, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.meca_bucket:
            self.logger.info(
                "%s, meca_bucket in settings is blank, skipping" % self.name
            )
            return self.ACTIVITY_SUCCESS

        self.make_activity_directories()

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        expanded_folder = session.get_value("expanded_folder")
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        version_doi = session.get_value("version_doi")

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # get a list of all bucket expanded_folder object names
        storage_resource_path = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        self.logger.info(
            "%s, storage_resource_path: %s" % (self.name, storage_resource_path)
        )

        expanded_folder_files = storage.list_resources(storage_resource_path)

        self.logger.info(
            "%s, expanded_folder_files: %s" % (self.name, expanded_folder_files)
        )

        # download all the S3 bucket expanded_folder contents
        for file_name in expanded_folder_files:
            local_file_name = file_name.rsplit(expanded_folder, 1)[-1].lstrip("/")
            local_file_path = os.path.join(
                self.directories.get("INPUT_DIR"), local_file_name
            )
            # create folders if they do not exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            storage_resource_origin = (
                self.settings.storage_provider
                + "://"
                + self.settings.bot_bucket
                + "/"
                + file_name
            )
            self.logger.info(
                "%s downloading %s to %s"
                % (self.name, storage_resource_origin, local_file_path)
            )
            try:
                with open(local_file_path, "wb") as open_file:
                    storage.get_resource_to_file(storage_resource_origin, open_file)
            except IsADirectoryError:
                # do not copy directories alone
                pass

        self.statuses["download"] = True

        # generate new meca file name
        meca_file_name = meca.meca_file_name(article_id, version)

        # add files to the meca (zip) file
        meca_file_path = os.path.join(
            self.directories.get("OUTPUT_DIR"), meca_file_name
        )

        self.logger.info("%s, creating MECA file %s" % (self.name, meca_file_path))

        article_processing.zip_files(
            zip_file_path=meca_file_path,
            folder_path=self.directories.get("INPUT_DIR"),
            caller_name=self.name,
            logger=self.logger,
        )

        self.statuses["zip"] = True

        # meca file S3 bucket path
        meca_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.meca_bucket
            + "/"
            + meca.MECA_BUCKET_FOLDER.lstrip("/").rstrip("/")
            + "/"
            + meca_file_name
        )

        # upload meca (zip) file to the bucket
        self.logger.info(
            "%s uploading %s to %s" % (self.name, meca_file_path, meca_resource)
        )
        storage.set_resource_from_filename(meca_resource, meca_file_path)
        self.statuses["upload"] = True
        # Clean up disk
        self.clean_tmp_dir()

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        return self.ACTIVITY_SUCCESS
