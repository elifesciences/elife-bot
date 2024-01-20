import os
import json
import time
from elifecleaner.transform import ArticleZipFile
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, email_provider, utils
from activity.objects import AcceptedBaseActivity


class activity_AcceptedSubmissionPeerReviewFigs(AcceptedBaseActivity):
    "AcceptedSubmissionPeerReviewFigs activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionPeerReviewFigs, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionPeerReviewFigs"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Transform certain peer review inline graphic image content into "
            "fig tags and images."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "hrefs": None,
            "modify_xml": None,
            "rename_files": None,
            "email": None,
        }

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
            self.end_cleaner_log(session)
            return True

        self.statuses["hrefs"] = True

        xml_root = cleaner.parse_article_xml(xml_file_path)

        file_transformations = []
        for sub_article_index, sub_article_root in enumerate(
            xml_root.iterfind("./sub-article")
        ):
            # list of old file names
            previous_hrefs = cleaner.inline_graphic_hrefs(
                sub_article_root, input_filename
            )
            cleaner.transform_fig(sub_article_root, input_filename)
            # list of new file names
            current_hrefs = cleaner.graphic_hrefs(sub_article_root, input_filename)
            # add to file_transformations
            self.logger.info(
                "%s, sub-article %s previous_hrefs: %s"
                % (self.name, sub_article_index, previous_hrefs)
            )
            self.logger.info(
                "%s, sub-article %s current_hrefs: %s"
                % (self.name, sub_article_index, current_hrefs)
            )
            for index, previous_href in enumerate(previous_hrefs):
                current_href = current_hrefs[index]
                from_file = ArticleZipFile(previous_href)
                to_file = ArticleZipFile(current_href)
                file_transformations.append((from_file, to_file))
        self.logger.info(
            "%s, total file_transformations: %s"
            % (self.name, len(file_transformations))
        )
        self.logger.info(
            "%s, file_transformations: %s" % (self.name, file_transformations)
        )

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

        # find duplicates in file_transformations
        copy_file_transformations = []
        copy_delete_file_transformations = []
        transformation_keys = []
        for file_transformation in file_transformations:
            if file_transformation[0].xml_name in transformation_keys:
                # this is a duplicate key
                copy_file_transformations.append(file_transformation)
            else:
                # this is a new key
                copy_delete_file_transformations.append(file_transformation)
                transformation_keys.append(file_transformation[0].xml_name)

        # rewrite the XML file with the renamed files
        if file_transformations:
            self.statuses["modify_xml"] = self.rewrite_file_tags(
                xml_file_path, copy_delete_file_transformations, input_filename
            )
            # add file tags for duplicate files
            self.add_file_tags(xml_file_path, copy_file_transformations, input_filename)

        # copy duplicate files in the expanded folder
        if self.statuses["modify_xml"]:
            try:
                self.statuses["rename_files"] = self.copy_expanded_folder_files(
                    asset_file_name_map,
                    expanded_folder,
                    copy_file_transformations,
                    storage,
                )
            except RuntimeError as exception:
                log_message = (
                    "%s, exception in rewrite_file_tags for duplicate file %s"
                    % (
                        self.name,
                        input_filename,
                    )
                )
                self.logger.exception(log_message)
                body_content = error_email_body_content(
                    "copy_expanded_folder_files",
                    input_filename,
                    self.name,
                )
                self.statuses["email"] = self.send_error_email(
                    input_filename, body_content
                )
                self.log_statuses(input_filename)
                return self.ACTIVITY_PERMANENT_FAILURE

        # rename the files in the expanded folder
        if self.statuses["modify_xml"]:
            try:
                self.statuses["rename_files"] = self.rename_expanded_folder_files(
                    asset_file_name_map,
                    expanded_folder,
                    copy_delete_file_transformations,
                    storage,
                )
            except RuntimeError as exception:
                log_message = "%s, exception in rewrite_file_tags for file %s" % (
                    self.name,
                    input_filename,
                )
                self.logger.exception(log_message)
                body_content = error_email_body_content(
                    "rename_expanded_folder_files",
                    input_filename,
                    self.name,
                )
                self.statuses["email"] = self.send_error_email(
                    input_filename, body_content
                )
                self.log_statuses(input_filename)
                return self.ACTIVITY_PERMANENT_FAILURE

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
    return "%sError in accepted submission peer review figs: %s" % (
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
