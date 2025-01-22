import os
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, github_provider, meca, peer_review
from activity.objects import MecaBaseActivity


FAIL_IF_NO_IMAGES_DOWNLOADED = False


class activity_MecaPeerReviewImages(MecaBaseActivity):
    "MecaPeerReviewImages activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaPeerReviewImages, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaPeerReviewImages"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Download peer review images to the S3 bucket and modify the MECA XML."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "download": None,
            "hrefs": None,
            "external_hrefs": None,
            "upload_xml": None,
        }

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # load session data
        run = data["run"]
        session = get_session(self.settings, data, run)
        article_xml_path = session.get_value("article_xml_path")
        expanded_folder = session.get_value("expanded_folder")
        version_doi = session.get_value("version_doi")
        article_id = session.get_value("article_id")

        # configure the S3 bucket storage library
        storage = storage_context(self.settings)

        # configure log files for the cleaner provider
        self.start_cleaner_log()

        # local path to the article XML file
        xml_file_path = os.path.join(self.directories.get("TEMP_DIR"), article_xml_path)

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # download XML from the bucket folder
        xml_storage_resource_origin = resource_prefix + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, xml_storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(xml_storage_resource_origin, open_file)

        # download manifest XML file
        (
            manifest_xml_file_path,
            manifest_storage_resource_origin,
        ) = self.download_manifest(storage, resource_prefix)

        self.statuses["download"] = True

        # search XML file for graphic tags
        inline_graphic_tags = cleaner.inline_graphic_tags(xml_file_path)
        if not inline_graphic_tags:
            self.logger.info(
                "%s, no inline-graphic tags in %s" % (self.name, version_doi)
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
                % (self.name, version_doi)
            )
            self.end_cleaner_log(session)
            return True

        self.statuses["external_hrefs"] = True

        approved_hrefs = cleaner.approved_inline_graphic_hrefs(external_hrefs)
        # add log messages if an external href is not approved to download
        if approved_hrefs and external_hrefs != approved_hrefs:
            not_approved_hrefs = sorted(set(external_hrefs) - set(approved_hrefs))
            for href in [href for href in external_hrefs if href in not_approved_hrefs]:
                log_message = (
                    "%s peer review image href was not approved for downloading" % href
                )
                self.logger.warning(log_message)
                meca.log_to_session("\n%s" % log_message, session)

        # download images to the local disk
        href_to_file_name_map = peer_review.download_images(
            approved_hrefs,
            self.directories.get("INPUT_DIR"),
            self.name,
            self.logger,
            getattr(self.settings, "user_agent", None),
        )

        self.logger.info(
            "%s, %s href_to_file_name_map: %s"
            % (self.name, version_doi, href_to_file_name_map)
        )

        # if images are not downloaded, add a Github issue comment
        if approved_hrefs and href_to_file_name_map.keys() != approved_hrefs:
            not_downloaded_hrefs = sorted(
                set(approved_hrefs) - set(href_to_file_name_map.keys())
            )
            for href in [
                href for href in approved_hrefs if href in not_downloaded_hrefs
            ]:
                log_message = (
                    "%s, peer review image %s was not downloaded successfully for %s"
                    % (self.name, href, version_doi)
                )
                self.logger.warning(log_message)
                meca.log_to_session("\n%s" % log_message, session)
                # add as a Github issue comment
                issue_comment = "elife-bot workflow message:\n\n%s" % log_message
                github_provider.add_github_issue_comment(
                    self.settings, self.logger, self.name, version_doi, issue_comment
                )

        # handle if no images were downloaded
        if not href_to_file_name_map:
            log_message = "%s, no images were downloaded for %s" % (
                self.name,
                version_doi,
            )
            self.logger.warning(log_message)
            # add as a Github issue comment
            issue_comment = "elife-bot workflow message:\n\n%s" % log_message
            github_provider.add_github_issue_comment(
                self.settings, self.logger, self.name, version_doi, issue_comment
            )

            # based on the flag, fail the workflow, or allow it to continue
            if FAIL_IF_NO_IMAGES_DOWNLOADED:
                self.logger.info("%s statuses: %s" % (self.name, self.statuses))
                return self.ACTIVITY_PERMANENT_FAILURE
            self.end_cleaner_log(session)
            return True

        content_subfolder = meca.meca_content_folder(article_xml_path)

        # rename the files, in the order as remembered by the OrderedDict
        file_details_list = peer_review.generate_new_image_file_names(
            href_to_file_name_map,
            article_id,
            identifier=version_doi,
            caller_name=self.name,
            logger=self.logger,
        )
        self.logger.info(
            "%s, %s image file name file_details_list: %s"
            % (self.name, version_doi, file_details_list)
        )
        file_details_list = peer_review.generate_new_image_file_paths(
            file_details_list,
            content_subfolder=content_subfolder,
            identifier=version_doi,
            caller_name=self.name,
            logger=self.logger,
        )
        self.logger.info(
            "%s, %s image file path file_details_list: %s"
            % (self.name, version_doi, file_details_list)
        )
        href_to_file_name_map = peer_review.modify_href_to_file_name_map(
            href_to_file_name_map, file_details_list
        )
        self.logger.info(
            "%s, %s modified href_to_file_name_map: %s"
            % (self.name, version_doi, file_details_list)
        )
        image_asset_file_name_map = peer_review.move_images(
            file_details_list,
            to_dir=self.directories.get("TEMP_DIR"),
            identifier=version_doi,
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

        # add to XML manifest <item> tags
        cleaner.add_item_tags_to_manifest_xml(
            manifest_xml_file_path, file_details_list, version_doi
        )

        # change inline-graphic xlink:href value
        cleaner.change_inline_graphic_xlink_hrefs(
            xml_file_path, href_to_file_name_map, version_doi
        )

        # upload the XML to the bucket
        self.logger.info(
            "%s, updating transformed XML to %s" % (self.name, s3_resource)
        )
        storage.set_resource_from_filename(xml_storage_resource_origin, xml_file_path)

        # upload manifest to the bucket
        self.logger.info("%s, updating manifest XML to %s" % (self.name, s3_resource))
        storage.set_resource_from_filename(
            manifest_storage_resource_origin, manifest_xml_file_path
        )

        self.statuses["upload_xml"] = True

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        self.end_cleaner_log(session)

        # Clean up disk
        self.clean_tmp_dir()

        return True
