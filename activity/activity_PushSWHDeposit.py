import json
import re
import os
import zipfile
from xml.etree import ElementTree
from provider.execution_context import get_session
from provider import software_heritage
from provider.storage_provider import storage_context
from activity.objects import Activity

DESCRIPTION_PATTERN = 'ERA complement for "%s", %s'
# maximum size of each zip file part when splitting apart large zip files
MAX_ZIP_SIZE_IN_BYTES = 50000000


class activity_PushSWHDeposit(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PushSWHDeposit, self).__init__(
            settings, logger, client, token, activity_task
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
                "%s, software_heritage_deposit_endpoint setting is empty or missing"
                % self.name
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

        # add README file, if present
        if session.get_value("bucket_readme_resource"):
            readme_file_path = download_bucket_resource(
                self.settings,
                session.get_value("bucket_readme_resource"),
                self.directories.get("INPUT_DIR"),
                self.logger,
            )
            with zipfile.ZipFile(
                zip_file_path, "a", zipfile.ZIP_DEFLATED, allowZip64=True
            ) as open_zip:
                open_zip.write(readme_file_path, arcname="README.md")
            self.logger.info(
                "%s, added README.md file to the zip %s" % (self.name, zip_file_path)
            )

        """
        In order to support sending larger files to Software Heritage, follow a
        particular set of requests to their API, setting the In-Progress header value
        to True as each file is uploaded, until the final file use In-Progress of False
        """

        # preparatory step, break up the zip file into smaller zip file chunks
        new_zip_files = split_zip_file(
            zip_file_path,
            self.directories.get("TMP_DIR"),
            self.logger,
            max_zip_size=MAX_ZIP_SIZE_IN_BYTES,
        )
        self.logger.info(
            "%s, ready to send %s zip files" % (self.name, len(new_zip_files))
        )

        # first API request, part one, upload the first file
        first_request_url = "%s/%s/" % (
            self.settings.software_heritage_deposit_endpoint,
            self.settings.software_heritage_collection_name,
        )
        first_zip_file_path = os.path.join(
            self.directories.get("TMP_DIR"), new_zip_files[0]
        )
        # if there is only one zip file to upload, use in_progress False
        in_progress = True
        if len(new_zip_files) == 1:
            in_progress = False
        try:
            response = self.post_file_to_swh(
                endpoint_url=first_request_url,
                article_id=article_id,
                zip_file_path=first_zip_file_path,
                atom_file_path=atom_file_path,
                in_progress=in_progress,
            )

        except Exception as exception:
            self.logger.exception(
                "Exception in %s posting first file to endpoint, workflow permanent failure"
                % self.name,
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # first API request, part two, get the URI of this upload to which we can send more files
        edit_request_url = endpoint_from_response(response.content)
        self.logger.info(
            "%s, endpoint for sending additional files: %s"
            % (self.name, edit_request_url)
        )

        # send multiple files in a loop if there is more than two files to upload
        if len(new_zip_files) > 2:
            file_count = 2
            # second phase, send each additional file as a separate request
            for new_zip_file in new_zip_files[1:-1]:
                self.logger.info(
                    "%s, sending zip file %s of %s"
                    % (self.name, file_count, len(new_zip_files))
                )
                zip_file_path = os.path.join(
                    self.directories.get("TMP_DIR"), new_zip_file
                )
                try:
                    response = self.post_file_to_swh(
                        endpoint_url=edit_request_url,
                        article_id=article_id,
                        zip_file_path=zip_file_path,
                        atom_file_path=None,
                        in_progress=True,
                    )

                except Exception as exception:
                    self.logger.exception(
                        "Exception in %s posting file %s to endpoint, workflow permanent failure"
                        % (self.name, new_zip_file),
                    )
                    return self.ACTIVITY_PERMANENT_FAILURE

                file_count = file_count + 1

        # third and final request, upload the final file with In-Progress False header
        if len(new_zip_files) > 1:
            final_zip_file_path = os.path.join(
                self.directories.get("TMP_DIR"), new_zip_files[-1]
            )
            try:
                response = self.post_file_to_swh(
                    endpoint_url=edit_request_url,
                    article_id=article_id,
                    zip_file_path=final_zip_file_path,
                    atom_file_path=None,
                    in_progress=False,
                )

            except Exception as exception:
                self.logger.exception(
                    "Exception in %s posting final file to endpoint, workflow permanent failure"
                    % self.name,
                )
                return self.ACTIVITY_PERMANENT_FAILURE

        # clean temporary directory
        self.clean_tmp_dir()

        # return success
        return self.ACTIVITY_SUCCESS

    def post_file_to_swh(
        self, endpoint_url, article_id, zip_file_path, atom_file_path, in_progress
    ):
        try:
            response = software_heritage.swh_post_request(
                endpoint_url,
                self.settings.software_heritage_auth_user,
                self.settings.software_heritage_auth_pass,
                zip_file_path=zip_file_path,
                atom_file_path=atom_file_path,
                in_progress=in_progress,
                logger=self.logger,
            )
            self.logger.info(
                "%s, finished post request to %s, file paths: %s"
                % (
                    self.name,
                    endpoint_url,
                    ", ".join([str(zip_file_path), str(atom_file_path)]),
                )
            )

        except Exception as exception:
            self.logger.exception(
                "Exception in %s posting to SWH API endpoint, article_id %s: %s"
                % (self.name, article_id, str(exception)),
            )
            raise

        return response


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


def split_zip_file(zip_file_path, output_dir, logger, max_zip_size=0):
    "create a new zip file for each file in the original zip file"
    zip_file_name = zip_file_path.split(os.sep)[-1]
    # remove the .zip file extension
    zip_file_name_start = ".".join(zip_file_name.split(".")[:-1])
    with zipfile.ZipFile(
        zip_file_path, "r", zipfile.ZIP_DEFLATED, allowZip64=True
    ) as open_zip:
        open_zip_info_list = open_zip.infolist()
        part_count = 1
        new_zip_filename = None

        for zip_info in sorted(
            open_zip_info_list, key=lambda zip_info: zip_info.filename
        ):
            if zip_info.filename.endswith("/"):
                logger.info(
                    'split_zip_file, "%s" ends with a slash, skipping it'
                    % zip_info.filename
                )
                continue

            if not new_zip_filename:
                new_zip_filename = "%s_part%s.zip" % (
                    zip_file_name_start,
                    "{:04d}".format(part_count),
                )
            new_zip_filename_path = os.path.join(output_dir, new_zip_filename)

            logger.info(
                'split_zip_file, "%s" new zip file name "%s"'
                % (zip_info.filename, new_zip_filename)
            )

            with zipfile.ZipFile(
                new_zip_filename_path,
                "a",
                zipfile.ZIP_DEFLATED,
            ) as new_zip:
                new_zip.writestr(zip_info, open_zip.read(zip_info))

            # check size of zip file exceeds the max, and whether to start writing a new one
            zip_file_size = os.path.getsize(new_zip_filename_path)
            if zip_file_size > max_zip_size:
                logger.info(
                    "zip file %s size of %s bytes exceeds maximum of %s bytes, "
                    "it will not be written to again"
                    % (new_zip_filename, zip_file_size, max_zip_size)
                )
                new_zip_filename = None
                part_count += 1
    return sorted(os.listdir(output_dir))


def endpoint_from_response(response_string):
    "from the API response XML, get the endpoint where more media can be posted"
    root = ElementTree.fromstring(response_string)
    link_tag = root.find('{http://www.w3.org/2005/Atom}link[@rel="edit-media"]')
    return link_tag.get("href")
