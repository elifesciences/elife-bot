from datetime import datetime
import json
import os
import zipfile
from xml.etree import ElementTree
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import (
    cleaner,
    docmap_provider,
    download_helper,
    utils,
)
from activity.objects import Activity


# DOI prefix for generating DOI value
DOI_PREFIX = "10.7554/eLife."


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

        # store details in session
        run = data["run"]
        article_id = data.get("article_id")
        version = data.get("version")
        session = get_session(self.settings, data, run)
        session.store_value("run", run)
        session.store_value("article_id", article_id)
        session.store_value("version", version)

        # get docmap as a string
        self.logger.info(
            "%s, getting docmap_string for article_id %s" % (self.name, article_id)
        )
        try:
            docmap_string = cleaner.get_docmap_string_with_retry(
                self.settings, article_id, self.name, self.logger
            )
            self.statuses["docmap_string"] = True
            # save the docmap_string to the session
            session.store_value(
                "docmap_datetime_string",
                datetime.strftime(utils.get_current_datetime(), utils.DATE_TIME_FORMAT),
            )
            session.store_value("docmap_string", docmap_string.decode("utf-8"))
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting a docmap for article_id %s: %s"
                % (self.name, article_id, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # parse docmap JSON
        self.logger.info(
            "%s, parsing docmap_string for article_id %s" % (self.name, article_id)
        )
        try:
            docmap_json = json.loads(docmap_string)
        except Exception as exception:
            self.logger.exception(
                "%s, exception parsing docmap_string for article_id %s: %s"
                % (self.name, article_id, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        version_doi = "%s%s.%s" % (DOI_PREFIX, article_id, version)
        session.store_value("version_doi", version_doi)

        self.logger.info(
            "%s, version_doi %s for article_id %s, version %s"
            % (self.name, version_doi, article_id, version)
        )

        # get a version DOI step map from the docmap
        try:
            steps = steps_by_version_doi(
                docmap_json, version_doi, self.name, self.logger
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception in steps_by_version_doi for version DOI %s: %s"
                % (self.name, version_doi, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE
        if not steps:
            self.logger.info(
                "%s, found no docmap steps for version DOI %s"
                % (self.name, version_doi)
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # get computer-file url from the docmap
        computer_file_url = computer_file_url_from_steps(
            steps, version_doi, self.name, self.logger
        )
        if not computer_file_url:
            self.logger.info(
                "%s, computer_file_url not found in computer_file for version DOI %s"
                % (self.name, version_doi)
            )
            return self.ACTIVITY_PERMANENT_FAILURE
        self.logger.info(
            "%s, computer_file_url %s for version_doi %s"
            % (self.name, computer_file_url, version_doi)
        )

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

        try:
            # Download zip from S3
            self.logger.info("%s downloading %s" % (self.name, meca_filename))
            local_meca_file = download_helper.download_file_from_s3(
                self.settings,
                meca_filename,
                bucket_name,
                bucket_folder,
                self.directories.get("INPUT_DIR"),
            )
            self.logger.info(
                "%s downloaded %s to %s" % (self.name, meca_filename, local_meca_file)
            )

            # extract zip contents
            self.logger.info("%s expanding file %s" % (self.name, local_meca_file))
            with zipfile.ZipFile(local_meca_file) as open_zip_file:
                for zip_file_name in open_zip_file.namelist():
                    open_zip_file.extract(
                        zip_file_name, self.directories.get("TEMP_DIR")
                    )

            # get a list of files including the subfolder paths
            files = []
            with os.scandir(self.directories.get("TEMP_DIR")) as dir_iterator:
                for entry in dir_iterator:
                    # will ignore hidden files and directories
                    if not entry.name.startswith(".") and entry.is_file():
                        files.append(entry.name)
                    elif entry.is_dir():
                        files += [
                            "%s%s%s" % (entry.name, os.sep, subfolder_file)
                            # listdir will by default ignore hidden files
                            for subfolder_file in os.listdir(
                                os.path.join(
                                    self.directories.get("TEMP_DIR"), entry.name
                                )
                            )
                        ]

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
                "%s Exception when expanding MECA file %s: %s"
                % (self.name, meca_filename, str(exception))
            )
            self.clean_tmp_dir()
            return self.ACTIVITY_PERMANENT_FAILURE

        # find the article XML file path and save it to the session
        article_xml_path = get_meca_article_xml_path(
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


def steps_by_version_doi(docmap_json, version_doi, caller_name, logger):
    "get steps from the docmap for the version_doi"
    logger.info(
        "%s, getting a step map for version DOI %s" % (caller_name, version_doi)
    )
    try:
        step_map = docmap_provider.version_doi_step_map(docmap_json)
    except Exception as exception:
        logger.exception(
            "%s, exception getting a step map for version DOI %s: %s"
            % (caller_name, version_doi, str(exception))
        )
        raise

    return step_map.get(version_doi)


def computer_file_url_from_steps(steps, version_doi, caller_name, logger):
    "get the url of computer-file input from docmap steps"
    computer_file = None
    for step in steps:
        computer_file_list = docmap_provider.computer_files(step)
        if computer_file_list:
            computer_file = computer_file_list[0]
            break

    if not computer_file:
        logger.info(
            "%s, computer_file not found in steps for version DOI %s"
            % (caller_name, version_doi)
        )
        return None
    logger.info(
        "%s, computer_file %s for version_doi %s"
        % (caller_name, computer_file, version_doi)
    )

    return computer_file.get("url")


def get_meca_article_xml_path(folder_name, version_doi, caller_name, logger):
    "find manifest.xml and get the article XML tag href"
    # locate the bucket path to the manuscript XML file by reading the manifest.xml
    manifest_file_path = os.path.join(folder_name, "manifest.xml")
    try:
        with open(manifest_file_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
    except FileNotFoundError:
        logger.exception(
            "%s, manifest_file_path %s not found for version DOI %s"
            % (caller_name, manifest_file_path, version_doi)
        )
        return None
    xml_root = ElementTree.fromstring(xml_string)
    article_xml_path = None
    instance_tag = xml_root.find(
        './/{http://manuscriptexchange.org}instance[@media-type="application/xml"]'
    )
    if instance_tag is not None:
        article_xml_path = instance_tag.attrib.get("href")
    return article_xml_path
