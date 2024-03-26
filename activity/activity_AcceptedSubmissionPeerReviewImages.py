import os
import json
import shutil
import time
from collections import OrderedDict
import requests
from provider.article_processing import file_extension
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, email_provider, utils
from activity.objects import AcceptedBaseActivity


FILE_NAME_FORMAT = "elife-%s-inf%s.%s"

REQUESTS_TIMEOUT = 10

FAIL_IF_NO_IMAGES_DOWNLOADED = True


class activity_AcceptedSubmissionPeerReviewImages(AcceptedBaseActivity):
    "AcceptedSubmissionPeerReviewImages activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionPeerReviewImages, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionPeerReviewImages"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download peer review images to the S3 bucket"
            " and modify the accepted submission XML."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"hrefs": None, "external_hrefs": None, "upload_xml": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        session = get_session(self.settings, data, data["run"])

        self.make_activity_directories()

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        expanded_folder, input_filename, article_id = self.read_session(session)

        # get list of bucket objects from expanded folder
        asset_file_name_map = self.bucket_asset_file_name_map(expanded_folder)

        # find S3 object for article XML and download it
        xml_file_path = self.download_xml_file_from_bucket(asset_file_name_map)

        # search XML file for graphic tags
        inline_graphic_tags = cleaner.inline_graphic_tags(xml_file_path)
        if not inline_graphic_tags:
            self.logger.info(
                "%s, no inline-graphic tags in %s" % (self.name, input_filename)
            )
            return True

        self.statuses["hrefs"] = True

        # find inline-graphic with https:// sources
        external_hrefs = cleaner.external_hrefs(
            cleaner.tag_xlink_hrefs(inline_graphic_tags)
        )
        if not external_hrefs:
            self.logger.info(
                "%s, no inline-graphic tags with external href values in %s"
                % (self.name, input_filename)
            )
            return True

        self.statuses["external_hrefs"] = True

        approved_hrefs = cleaner.approved_inline_graphic_hrefs(external_hrefs)

        # add log messages if an external href is not approved to download
        if approved_hrefs and external_hrefs != approved_hrefs:
            not_approved_hrefs = sorted(set(external_hrefs) - set(approved_hrefs))
            for href in [href for href in external_hrefs if href in not_approved_hrefs]:
                cleaner.LOGGER.warning(
                    "%s peer review image href was not approved for downloading", href
                )

        # download images to the local disk
        href_to_file_name_map = download_images(
            approved_hrefs,
            self.directories.get("INPUT_DIR"),
            self.name,
            self.logger,
            getattr(self.settings, "user_agent", None),
        )

        # add log messages if an external href download was not successful
        if approved_hrefs and href_to_file_name_map.keys() != approved_hrefs:
            not_downloaded_hrefs = sorted(
                set(approved_hrefs) - set(href_to_file_name_map.keys())
            )
            for href in [
                href for href in approved_hrefs if href in not_downloaded_hrefs
            ]:
                cleaner.LOGGER.warning(
                    "%s peer review image href was not downloaded successfully", href
                )

        # do not continue if no images were downloaded
        if not href_to_file_name_map:
            self.logger.info(
                "%s, no images were downloaded for %s, returning True"
                % (self.name, input_filename)
            )
            body_content = error_email_body_content(
                "downloading images from imgur",
                input_filename,
                self.name,
            )
            self.statuses["email"] = self.send_error_email(input_filename, body_content)
            self.log_statuses(input_filename)

            # based on the flag, fail the workflow, or allow it to continue
            if FAIL_IF_NO_IMAGES_DOWNLOADED:
                return self.ACTIVITY_PERMANENT_FAILURE
            return True

        # subfolder on disk where assets are stored
        temp_dir_subfolder = cleaner.article_xml_asset(asset_file_name_map)[0].rsplit(
            os.sep, 1
        )[0]
        self.logger.info(
            "%s, temp_dir_subfolder for %s: %s"
            % (self.name, input_filename, temp_dir_subfolder)
        )

        # rename the files, in the order as remembered by the OrderedDict
        file_name_count = 1
        image_asset_file_name_map = {}
        file_details_list = []
        for href, file_name in href_to_file_name_map.items():
            new_file_name = FILE_NAME_FORMAT % (
                utils.pad_msid(article_id),
                file_name_count,
                file_extension(file_name),
            )
            self.logger.info(
                "%s, for %s, file name %s changed to file name %s"
                % (self.name, input_filename, file_name, new_file_name)
            )
            new_file_asset = os.path.join(temp_dir_subfolder, new_file_name)
            self.logger.info(
                "%s, for %s, file %s new asset value %s"
                % (self.name, input_filename, new_file_name, new_file_asset)
            )
            new_file_path = os.path.join(
                self.directories.get("TEMP_DIR"), new_file_asset
            )
            self.logger.info(
                "%s, for %s, moving %s to %s"
                % (self.name, input_filename, file_name, new_file_path)
            )
            # move the file on disk
            shutil.move(file_name, new_file_path)

            # change the file path in the href map
            href_to_file_name_map[href] = new_file_name
            # add the file path to the asset map
            image_asset_file_name_map[new_file_asset] = new_file_path
            # add the file details for using later to add XML file tags
            file_details = {"file_type": "figure", "upload_file_nm": new_file_name}
            file_details_list.append(file_details)

            # increment the file name counter
            file_name_count += 1

        # upload images to the bucket expanded files folder
        for upload_key, file_name in image_asset_file_name_map.items():
            s3_resource = (
                self.settings.storage_provider
                + "://"
                + self.settings.bot_bucket
                + "/"
                + expanded_folder
                + "/"
                + upload_key
            )
            local_file_path = file_name
            storage.set_resource_from_filename(s3_resource, local_file_path)
            self.logger.info(
                "%s, uploaded %s to S3 object: %s"
                % (self.name, local_file_path, s3_resource)
            )

        # add to XML manifest <file> tags
        cleaner.add_file_tags_to_xml(xml_file_path, file_details_list, input_filename)

        # change inline-graphic xlink:href value
        cleaner.change_inline_graphic_xlink_hrefs(
            xml_file_path, href_to_file_name_map, input_filename
        )

        # upload the XML to the bucket
        self.upload_xml_file_to_bucket(asset_file_name_map, expanded_folder, storage)

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True

    def send_error_email(self, output_file, body_content):
        "email the message to the recipients"
        success = True

        datetime_string = time.strftime(utils.DATE_TIME_FORMAT, time.gmtime())
        body = email_provider.simple_email_body(datetime_string, body_content)
        subject = error_email_subject(output_file, self.settings)
        sender_email = self.settings.accepted_submission_sender_email
        recipient_email_list = email_provider.list_email_recipients(
            self.settings.accepted_submission_validate_error_recipient_email
        )

        connection = email_provider.smtp_connect(self.settings, self.logger)
        # send the emails
        for recipient in recipient_email_list:
            # create the email
            email_message = email_provider.message(subject, sender_email, recipient)
            email_provider.add_text(email_message, body)
            # send the email
            email_success = email_provider.smtp_send(
                connection, sender_email, recipient, email_message, self.logger
            )
            if not email_success:
                # for now any failure in sending a mail return False
                success = False
        return success


def download_images(href_list, to_dir, activity_name, logger, user_agent=None):
    href_to_file_name_map = OrderedDict()
    for href in href_list:
        file_name = href.rsplit("/", 1)[-1]
        to_file = os.path.join(to_dir, file_name)
        # todo!!! improve handling of potentially duplicate file_name values
        if href in href_to_file_name_map.keys():
            logger.info("%s, href %s was already downloaded" % (activity_name, href))
            continue
        try:
            file_path = download_file(href, to_file, user_agent)
        except RuntimeError as exception:
            logger.info(str(exception))
            logger.info("%s, href %s could not be downloaded" % (activity_name, href))
            continue
        logger.info("%s, downloaded href %s to %s" % (activity_name, href, to_file))
        # keep track of a map of href value to local file_name
        href_to_file_name_map[href] = file_path
    return href_to_file_name_map


def download_file(from_path, to_file, user_agent=None):
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    request = requests.get(from_path, timeout=REQUESTS_TIMEOUT, headers=headers)
    if request.status_code == 200:
        with open(to_file, "wb") as open_file:
            open_file.write(request.content)
        return to_file
    raise RuntimeError(
        "GET request returned a %s status code for %s"
        % (request.status_code, from_path)
    )


def error_email_subject(output_file, settings=None):
    "the email subject"
    subject_prefix = ""
    if utils.settings_environment(settings) == "continuumtest":
        subject_prefix = "TEST "
    return "%sError in accepted submission peer review images: %s" % (
        subject_prefix,
        output_file,
    )


def error_email_body_content(
    action_type,
    input_filename,
    activity_name,
):
    "body content of the error email"
    body_content = (
        ("An exception was raised in %s" " when %s" " processing input file %s\n\n")
    ) % (activity_name, action_type, input_filename)
    return body_content
