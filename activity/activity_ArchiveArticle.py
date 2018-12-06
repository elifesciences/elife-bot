import os
import json
import zipfile
from datetime import datetime
from provider.storage_provider import storage_context
from activity.objects import Activity

"""
activity_ArchiveArticle.py activity
"""


class activity_ArchiveArticle(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_ArchiveArticle, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "ArchiveArticle"
        self.pretty_name = "Archive Article"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Archive an article post-publication"
        self.logger = logger

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            self.emit_monitor_event(self.settings, data['article_id'], data['version'],
                                    data['run'], self.pretty_name,
                                    "start", "Starting archiving article " + data['article_id'])

            article_id = data['article_id']
            version = data['version']
            expanded_folder = data['expanded_folder']
            update_date_string = data['update_date']
            updated_date = datetime.strptime(update_date_string, "%Y-%m-%dT%H:%M:%SZ")
            status = data['status'].lower()

            zip_dir_name = zip_dir(article_id, status, version, updated_date)
            zip_dir_path = create_zip_dir(self.get_tmp_dir(), zip_dir_name)
            bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.expanded_bucket)

            downloaded = self.download_files(bucket_name, expanded_folder, zip_dir_path)
            if not downloaded:
                error_message = "Failed to download all files in ArchiveArticle"
                self.logger.error(error_message)
                self.emit_monitor_event(self.settings, data['article_id'], version,
                                        data["run"], self.pretty_name,
                                        "error", "Error archiving article " + data['article_id'] +
                                        " message:" + error_message)
                return self.ACTIVITY_PERMANENT_FAILURE

            zip_path = self.zip_files(zip_dir_name, zip_dir_path)

            output_bucket_name = (
                self.settings.publishing_buckets_prefix + self.settings.archive_bucket)
            self.upload_zip(output_bucket_name, zip_path)

            self.clean_tmp_dir()

        except Exception as exception:
            self.logger.exception("Exception when archiving article. Message:" + str(exception))
            self.emit_monitor_event(self.settings, data['article_id'], version,
                                    data["run"], self.pretty_name,
                                    "error", "Error archiving article " + data['article_id'] +
                                    " message:" + str(exception))

            return self.ACTIVITY_PERMANENT_FAILURE

        self.emit_monitor_event(self.settings, data['article_id'], version,
                                data["run"], self.pretty_name,
                                "end", "Finished archiving article " + data['article_id'] +
                                " for version " + version + " run " + data["run"])

        return self.ACTIVITY_SUCCESS

    def download_files(self, bucket_name, expanded_folder, zip_dir_path):
        "download files from the expanded folder"
        # download expanded folder
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        orig_resource = storage_provider + bucket_name + "/" + expanded_folder
        self.logger.info("ArchiveArticle listing files from %s", orig_resource)
        files_in_bucket = storage.list_resources(orig_resource)
        self.logger.info("files_in_bucket: %s", files_in_bucket)
        try:
            for key_name in files_in_bucket:
                file_name = key_name.split('/')[-1]
                file_path = os.path.join(zip_dir_path, file_name)
                storage_resource_origin = orig_resource + '/' + file_name
                with open(file_path, 'wb') as open_file:
                    self.logger.info("Downloading %s to %s", (storage_resource_origin, file_path))
                    storage.get_resource_to_file(storage_resource_origin, open_file)
        except IOError as exception:
            self.logger.exception(
                "Failed to download file %s. details: %s" % key_name, str(exception))
            return None
        return True

    def zip_files(self, zip_dir_name, zip_dir_path):
        "add the files to a zip"
        # rename downloaded folder
        zip_path = os.path.join(self.get_tmp_dir(), zip_dir_name) + '.zip'
        # zip expanded folder
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as open_zip:
            self.logger.info("Opened zip file %s", zip_path)
            for root, dirs, files in os.walk(zip_dir_path):
                for dir_file in files:
                    filename = os.path.join(root, dir_file)
                    if os.path.isfile(filename):
                        self.logger.info("Adding file %s to zip file %s", (filename, zip_path))
                        # Archive file name, effectively make the
                        # zip_dir the root directory by stripping it from the file name f
                        arcname = root.rstrip(zip_dir_path) + dir_file
                        open_zip.write(filename, arcname)
        return zip_path

    def upload_zip(self, output_bucket_name, file_name_path):
        "upload the zip to the archive bucket"
        # Get the file name from the full file path
        file_name = file_name_path.split(os.sep)[-1]

        # Create S3 object and save
        bucket_name = output_bucket_name
        storage = storage_context(self.settings)
        storage_provider = self.settings.storage_provider + "://"
        s3_folder_name = ""
        resource_dest = storage_provider + bucket_name + "/" + s3_folder_name + file_name
        storage.set_resource_from_filename(resource_dest, file_name_path)
        self.logger.info("Copied %s to %s", file_name_path, resource_dest)


def zip_dir(article_id, status, version, updated_date):
    "zip directory name"
    return ("elife-" + article_id + '-' + status + '-v' + version
            + '-' + updated_date.strftime('%Y%m%d%H%M%S'))


def create_zip_dir(parent_dir, zip_dir_name):
    "create the directory on disk to copy files into"
    zip_dir_path = os.path.join(parent_dir, zip_dir_name)
    os.mkdir(zip_dir_path)
    return zip_dir_path
