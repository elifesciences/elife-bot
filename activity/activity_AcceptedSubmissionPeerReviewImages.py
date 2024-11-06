import os
import json
import time
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, email_provider, peer_review, utils
from activity.objects import AcceptedBaseActivity


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
        href_to_file_name_map = peer_review.download_images(
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
        file_details_list = peer_review.generate_new_image_file_names(
            href_to_file_name_map,
            article_id,
            identifier=input_filename,
            caller_name=self.name,
            logger=self.logger,
        )
        file_details_list = peer_review.generate_new_image_file_paths(
            file_details_list,
            content_subfolder=temp_dir_subfolder,
            identifier=input_filename,
            caller_name=self.name,
            logger=self.logger,
        )
        href_to_file_name_map = peer_review.modify_href_to_file_name_map(
            href_to_file_name_map, file_details_list
        )
        image_asset_file_name_map = peer_review.move_images(
            file_details_list,
            to_dir=self.directories.get("TEMP_DIR"),
            identifier=input_filename,
            caller_name=self.name,
            logger=self.logger,
        )

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
