import os
from datetime import datetime
import json
from activity.objects import Activity
from provider import (
    docmap_provider,
    utils,
)
from provider.execution_context import get_session
from provider.storage_provider import storage_context


# path to save docmap index in the bucket run folder
DOCMAP_INDEX_BUCKET_PATH = "docmap_index/docmap_index.json"


class activity_DownloadDocmapIndex(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_DownloadDocmapIndex, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "DownloadDocmapIndex"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 15
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 15
        self.description = (
            "Download docmap index JSON, save it to S3, and populate the session"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
        }

        # Bucket for published files
        self.publish_bucket = settings.poa_packaging_bucket
        self.bucket_folder = self.s3_bucket_folder(self.name) + "/"

        # Track the success of some steps
        self.statuses = {}

    def do_activity(self, data=None):
        "Activity, do the work" ""
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        # check for required settings
        if not hasattr(self.settings, "docmap_index_url"):
            self.logger.info(
                "%s, docmap_index_url in settings is missing, skipping" % self.name
            )
            return True
        if not self.settings.docmap_index_url:
            self.logger.info(
                "%s, docmap_index_url in settings is blank, skipping" % self.name
            )
            return True

        # Create output directories
        self.make_activity_directories()

        # load a session
        run = data["run"]
        session = get_session(self.settings, data, run)

        # get docmap index JSON
        try:
            docmap_index_json = docmap_provider.get_docmap_index_json(
                self.settings, self.name, self.logger
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting a docmap index: %s" % (self.name, str(exception))
            )
            self.logger.info("%s, ")
            return self.ACTIVITY_PERMANENT_FAILURE
        if not docmap_index_json:
            self.logger.exception("%s, docmap_index_json was None" % self.name)
            return self.ACTIVITY_PERMANENT_FAILURE
        if not docmap_index_json.get("docmaps"):
            self.logger.exception(
                "%s, docmaps in docmap_index_json was empty" % self.name
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        docmap_index_json_path = os.path.join(
            self.directories.get("TEMP_DIR"), "docmap_index.json"
        )
        self.logger.info(
            "%s, saving docmap_index_json to %s" % (self.name, docmap_index_json_path)
        )
        with open(docmap_index_json_path, "w", encoding="utf-8") as open_file:
            open_file.write(json.dumps(docmap_index_json))

        # get previous run folder name from S3 bucket
        storage = storage_context(self.settings)
        run_folder_bucket_path = (
            self.settings.storage_provider
            + "://"
            + self.publish_bucket
            + "/"
            + self.bucket_folder
        )

        prev_run_folder = previous_run_folder(storage, run_folder_bucket_path)
        prev_run_folder_bucket_path = None
        self.logger.info("%s, prev_run_folder: %s" % (self.name, prev_run_folder))
        if prev_run_folder:
            prev_run_folder_bucket_path = "%s%s/" % (
                run_folder_bucket_path,
                prev_run_folder,
            )
        self.logger.info(
            "%s, prev_run_folder_bucket_path: %s"
            % (self.name, prev_run_folder_bucket_path)
        )

        # save previous docmap index resource location to the session
        if prev_run_folder_bucket_path:
            prev_run_docmap_index_resource = "%s%s" % (
                prev_run_folder_bucket_path,
                DOCMAP_INDEX_BUCKET_PATH,
            )
            self.logger.info(
                "%s, saving prev_run_docmap_index_resource %s to session"
                % (
                    self.name,
                    prev_run_docmap_index_resource,
                )
            )
            session.store_value(
                "prev_run_docmap_index_resource", prev_run_docmap_index_resource
            )

        # new run folder name, based on the immediately previous run folder name
        new_run_folder_name = new_run_folder(storage, run_folder_bucket_path)
        new_run_docmap_index_resource = "%s%s/%s" % (
            run_folder_bucket_path,
            new_run_folder_name,
            DOCMAP_INDEX_BUCKET_PATH,
        )
        self.logger.info(
            "%s, new_run_docmap_index_resource: %s"
            % (self.name, new_run_docmap_index_resource)
        )

        # upload docmap index JSON to the new run folder name in the S3 bucket
        self.logger.info(
            "%s, storing %s to %s"
            % (self.name, docmap_index_json_path, new_run_docmap_index_resource)
        )
        storage.set_resource_from_filename(
            new_run_docmap_index_resource, docmap_index_json_path
        )
        self.statuses["upload"] = True

        session.store_value(
            "new_run_docmap_index_resource", new_run_docmap_index_resource
        )

        # determine the success of the activity
        self.statuses["activity"] = self.statuses.get("upload")

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

        return True


RUN_FOLDER_PREFIX = "run_"


def date_from_run_folder(folder_name):
    "parse a date from a run folder name"
    try:
        date_string = "-".join(folder_name.split("_")[1:4])
    except AttributeError as exception:
        raise AttributeError("No date data found in %s" % folder_name) from exception
    try:
        return datetime.strptime("%s +0000" % date_string, "%Y-%m-%d %z")
    except ValueError as exception:
        raise ValueError("Could not parse date from %s" % folder_name) from exception


def run_folder_names(storage, resource):
    "get list of previous run folders from the bucket"
    # separate the bucket name from the other object path data
    bucket_name, bucket_path_prefix = storage.s3_storage_objects(resource)

    # full list of objects for the S3 prefix
    s3_key_names = storage.list_resources(resource)

    # match folder names by their start value
    starts_with = "%s%s" % (bucket_path_prefix.lstrip("/"), RUN_FOLDER_PREFIX)

    # filter by folder names only
    # avoid any subfolders by splitting by the delimiter count
    delimiter_count = starts_with.count("/")
    folders = [
        "/".join(key_name.split("/")[0 : delimiter_count + 1])
        for key_name in s3_key_names
        if key_name.count("/") > delimiter_count
    ]

    # list of run folder names
    run_folder_paths = [
        folder_path
        for folder_path in folders
        if folder_path.startswith(starts_with)
        and folder_path.count("/") == delimiter_count
    ]
    # strip away subfolder names and extra delimiter
    return sorted(
        [folder_name.rstrip("/").rsplit("/", 1)[-1] for folder_name in run_folder_paths]
    )


def new_run_folder(storage, bucket_path):
    "get a next run folder name"

    # get latest run folder index
    run_folders = run_folder_names(storage, bucket_path)
    date_string = datetime.strftime(utils.get_current_datetime(), "%Y_%m_%d")

    run_folder_prefix = "%s%s" % (RUN_FOLDER_PREFIX, date_string)
    filtered_run_folders = [
        folder_name
        for folder_name in run_folders
        if folder_name.startswith(run_folder_prefix)
    ]

    if filtered_run_folders:
        latest_run_folder = filtered_run_folders[-1]
        latest_run_index = int(latest_run_folder.rsplit("_", 1)[-1])
    else:
        latest_run_index = 0

    # increment to get the next run folder name
    return "%s_%s" % (run_folder_prefix, str(latest_run_index + 1).zfill(4))


def previous_run_folder(storage, bucket_path, from_folder=None):
    "find name of the previous run folder, previous to from_folder if specified"
    run_folders = run_folder_names(storage, bucket_path)

    if not run_folders:
        return None
    index = None
    # compare by the date value in the folder names
    if from_folder:
        from_date = date_from_run_folder(from_folder)
    else:
        from_date = utils.get_current_datetime()
    for idx, run_folder_name in enumerate(run_folders):
        if run_folder_name == from_folder:
            index = idx - 1
            break
        run_folder_date = date_from_run_folder(run_folder_name)
        if run_folder_date <= from_date:
            index = idx

    return run_folders[index]
