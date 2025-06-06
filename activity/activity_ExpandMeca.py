from functools import partial
import json
import os
import zipfile
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import (
    download_helper,
    github_provider,
    meca,
    sts,
    utils,
)
from activity.objects import Activity


class activity_ExpandMeca(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ExpandMeca, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ExpandMeca"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Expands a MECA file to a folder in an S3 bucket"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # S3 expanded folder prefix
        self.s3_folder_prefix = "expanded_meca"
        # S3 folder name to contain the expanded files and folders
        self.s3_files_folder = "expanded_files"

        # Track the success of some steps
        self.statuses = {"docmap_string": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # get details from session
        run = data["run"]
        session = get_session(self.settings, data, run)
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        version_doi = session.get_value("version_doi")
        computer_file_url = session.get_value("computer_file_url")

        # get bucket name, path, and file name
        storage = storage_context(self.settings)
        bucket_name, bucket_path_prefix = storage.s3_storage_objects(computer_file_url)
        meca_filename = bucket_path_prefix.rsplit("/", 1)[-1]
        bucket_folder = bucket_path_prefix.rsplit("/", 1)[0].lstrip("/")

        self.logger.info(
            "%s, meca_filename: %s, bucket_name: %s, bucket_folder: %s"
            % (self.name, meca_filename, bucket_name, bucket_folder)
        )

        # set the S3 bucket path to hold unzipped files
        expanded_folder = (
            self.s3_folder_prefix.lstrip("/").rstrip("/")
            + "/"
            + utils.pad_msid(article_id)
            + "-v%s" % version
            + "/"
            + run
            + "/"
            + self.s3_files_folder
        )
        self.logger.info(
            "%s, expanded folder %s for article_id %s, version %s"
            % (self.name, expanded_folder, article_id, version)
        )

        # get external bucket name list from the settings
        external_meca_bucket_list = getattr(
            self.settings, "external_meca_bucket_list", None
        )

        # Downlaod zip from external bucket
        if external_meca_bucket_list and bucket_name in external_meca_bucket_list:
            try:
                # Download zip from an external S3 bucket using an STS token
                self.logger.info(
                    "%s, will download from external bucket %s for article_id %s, version %s"
                    % (self.name, bucket_name, article_id, version)
                )
                download_settings = meca_assume_role(self.settings, self.logger)
            except Exception as exception:
                log_message = (
                    "%s, exception when assuming role to access bucket %s for %s"
                    % (self.name, bucket_name, meca_filename)
                )
                self.logger.exception("%s: %s" % (log_message, str(exception)))
                # add as a Github issue comment
                issue_comment = "elife-bot workflow message:\n\n%s" % log_message
                github_provider.add_github_issue_comment(
                    self.settings, self.logger, self.name, version_doi, issue_comment
                )
                self.clean_tmp_dir()
                return self.ACTIVITY_PERMANENT_FAILURE
        else:
            download_settings = self.settings

        try:
            # Download zip from S3
            self.logger.info("%s downloading %s" % (self.name, meca_filename))
            local_meca_file = download_helper.download_file_from_s3(
                download_settings,
                meca_filename,
                bucket_name,
                bucket_folder,
                self.directories.get("INPUT_DIR"),
            )
            self.logger.info(
                "%s downloaded %s to %s" % (self.name, meca_filename, local_meca_file)
            )

        except Exception as exception:
            self.logger.exception(
                "%s, exception when downloading MECA file %s: %s"
                % (self.name, meca_filename, str(exception))
            )
            self.clean_tmp_dir()
            return self.ACTIVITY_PERMANENT_FAILURE

        try:
            # extract zip contents
            self.logger.info("%s expanding file %s" % (self.name, local_meca_file))
            with zipfile.ZipFile(local_meca_file) as open_zip_file:
                for zip_file_name in open_zip_file.namelist():
                    open_zip_file.extract(
                        zip_file_name, self.directories.get("TEMP_DIR")
                    )

            # get a list of files including the subfolder paths
            files = []
            for root, dirs, file_names in os.walk(self.directories.get("TEMP_DIR")):
                for dir_file in file_names:
                    # ignore hidden files and directories
                    if root.rsplit(os.sep, 1)[-1].startswith(
                        "."
                    ) or dir_file.startswith("."):
                        self.logger.info(
                            "%s %s ignoring file: %s"
                            % (self.name, local_meca_file, os.path.join(root, dir_file))
                        )
                        continue
                    # strip the TEMP_DIR and add to list of files
                    files.append(
                        os.path.join(
                            root.rsplit(self.directories.get("TEMP_DIR"), 1)[-1].lstrip(
                                "/"
                            ),
                            dir_file,
                        )
                    )

            self.logger.info("%s %s files: %s" % (self.name, local_meca_file, files))

            # upload the files to the bucket
            for file_name in files:
                source_path = os.path.join(self.directories.get("TEMP_DIR"), file_name)
                dest_path = expanded_folder + "/" + file_name

                storage_resource_dest = (
                    self.settings.storage_provider
                    + "://"
                    + self.settings.bot_bucket
                    + "/"
                    + dest_path
                )
                self.logger.info(
                    "%s uploading %s to %s"
                    % (self.name, source_path, storage_resource_dest)
                )
                try:
                    storage.set_resource_from_filename(
                        storage_resource_dest, source_path
                    )
                except IsADirectoryError:
                    # do not copy directories alone
                    pass

            session.store_value("expanded_folder", expanded_folder)

        except Exception as exception:
            self.logger.exception(
                "%s, exception when expanding MECA file %s: %s"
                % (self.name, meca_filename, str(exception))
            )
            self.clean_tmp_dir()
            return self.ACTIVITY_PERMANENT_FAILURE

        # find the article XML file path and save it to the session
        article_xml_path = meca.get_meca_article_xml_path(
            self.directories.get("TEMP_DIR"), self.name, version_doi, self.logger
        )
        if not article_xml_path:
            self.logger.info(
                "%s, article_xml_path not found in manifest.xml for version DOI %s"
                % (self.name, version_doi)
            )
            self.clean_tmp_dir()
            return self.ACTIVITY_PERMANENT_FAILURE

        session.store_value("article_xml_path", article_xml_path)

        self.clean_tmp_dir()

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        return self.ACTIVITY_SUCCESS


class TemporarySettings:
    "object to hold settings from STS service"
    aws_access_key_id = None
    aws_secret_access_key = None
    aws_session_token = None
    region_name = None
    storage_provider = None
    _aws_conn_map = {}
    aws_conn = None


def meca_assume_role(settings, logger):
    "assume role and put credentials into a stub settings object"
    # role to assume
    role_arn = getattr(settings, "meca_sts_role_arn", None)
    if not role_arn:
        logger.info("no meca_sts_role_arn found in settings")
        return None
    # check for required session name
    role_session_name = getattr(settings, "meca_sts_role_session_name", None)
    if not role_session_name:
        logger.info("no meca_sts_role_session_name found in settings")
        return None

    # additional attributes to copy to the settings stub
    copy_attributes = ["region_name", "storage_provider"]

    # credentials to settings attribute map
    credentials_map = {
        "AccessKeyId": "aws_access_key_id",
        "SecretAccessKey": "aws_secret_access_key",
        "SessionToken": "aws_session_token",
    }

    # assume role and return response which includes new credentials
    sts_client = sts.get_client(settings)
    sts_response = sts.assume_role(
        sts_client,
        role_arn,
        role_session_name,
    )
    if not sts_response:
        logger.info("no STS response for role_arn %s" % role_arn)
        return None

    sts_credentials = sts_response.get("Credentials")

    if not sts_credentials:
        logger.info("no STS credentials for meca_sts_role_arn %s" % role_arn)
        return None

    # instantiate new settings
    new_settings = TemporarySettings()
    # copy settings attributes
    for key_name in copy_attributes:
        setattr(new_settings, key_name, getattr(settings, key_name, None))
    # set credentials attributes
    for cred_attr, settings_attr in credentials_map.items():
        setattr(new_settings, settings_attr, sts_credentials.get(cred_attr))
    # set the aws_conn property
    new_settings.aws_conn = partial(
        utils.get_aws_connection, new_settings._aws_conn_map
    )
    return new_settings
