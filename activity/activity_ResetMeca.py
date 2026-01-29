import os
import json
from elifetools import xmlio
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, meca, preprint
from activity.objects import MecaBaseActivity


class activity_ResetMeca(MecaBaseActivity):
    "ResetMeca activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_ResetMeca, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "ResetMeca"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Reset MECA files in the expanded folder to not include sub-article XML, images,"
            " and other post-publication data"
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "sub_article": None,
            "modify_xml": None,
            "modify_manifest_xml": None,
            "modify_files": None,
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

        # convert entities to unicode if present
        self.logger.info(
            "%s, converting entities to unicode in %s" % (self.name, xml_file_path)
        )
        preprint.repair_entities(xml_file_path, self.name, self.logger)

        # search XML for sub-article tags
        sub_article_tags = find_sub_article_tags(xml_file_path)
        if not sub_article_tags:
            self.logger.info("%s, no sub-article XML in %s" % (self.name, version_doi))
            self.statuses["sub_article"] = False
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            self.end_cleaner_log(session)
            return True

        self.statuses["sub_article"] = True

        # get graphic and inline-graphic tags in sub-article tags
        graphic_tags = []
        inline_graphic_tags = []
        for sub_article_tag in sub_article_tags:
            graphic_tags += find_graphic_tags(sub_article_tag)
            inline_graphic_tags += find_inline_graphic_tags(sub_article_tag)

        self.logger.info(
            "%s, found %s graphic in sub-article XML in %s"
            % (self.name, len(graphic_tags), version_doi)
        )
        self.logger.info(
            "%s, found %s inline-graphic in sub-article XML in %s"
            % (self.name, len(inline_graphic_tags), version_doi)
        )

        content_subfolder = meca.meca_content_folder(article_xml_path)

        # collect graphic file paths
        file_hrefs = []
        file_paths = []
        for tag in graphic_tags + inline_graphic_tags:
            href = cleaner.tag_xlink_href(tag)
            # skip any absolute URLs
            if href and (href.startswith("http://") or href.startswith("https://")):
                self.logger.info(
                    "%s, ignoring %s from image file removal list in %s"
                    % (self.name, href, version_doi)
                )
                continue
            if href:
                file_hrefs.append(href)
                path = "/".join([content_subfolder, href])
                file_paths.append(path)

        self.logger.info(
            "%s, file_paths %s for %s" % (self.name, file_paths, version_doi)
        )

        # remove the tags in the manifest.xml for the file_paths
        remove_file_detail_list = []
        if file_paths:
            # download manifest XML file
            (
                manifest_xml_file_path,
                manifest_storage_resource_origin,
            ) = self.download_manifest(storage, resource_prefix)

            # format file_details
            for path in file_paths:
                file_details = {}
                file_details["from_href"] = path
                # set href to None in order to remove item tags from the manifest.xml
                file_details["href"] = None
                remove_file_detail_list.append(file_details)

            # remove item tags in manifest file
            meca.rewrite_item_tags(
                manifest_xml_file_path,
                remove_file_detail_list,
                version_doi,
                self.name,
                self.logger,
            )

            # make manifest XML more pretty with added new line characters
            cleaner.pretty_manifest_xml(manifest_xml_file_path, version_doi)

            self.statuses["modify_manifest_xml"] = True

        # collect asset file name paths for s3 object copying routine
        if remove_file_detail_list:
            asset_file_name_map = {}
            for detail in remove_file_detail_list:
                if detail.get("from_href"):
                    asset_file_name_map[detail.get("from_href")] = detail.get(
                        "from_href"
                    )

            self.logger.info(
                "%s, %s asset_file_name_map: %s"
                % (self.name, version_doi, asset_file_name_map)
            )

            # delete the files in the expanded folder
            self.delete_expanded_folder_files(
                asset_file_name_map,
                resource_prefix,
                file_hrefs,
                storage,
            )

            self.statuses["modify_files"] = True

        # remove the sub-article XML from the MECA XML
        xml_root = cleaner.parse_article_xml(xml_file_path)
        remove_sub_article_tags(xml_root)

        # get the XML doctype
        root, doctype_dict, processing_instructions = xmlio.parse(
            xml_file_path,
            return_doctype_dict=True,
            return_processing_instructions=True,
            insert_pis=True,
            insert_comments=True,
        )

        cleaner.pretty_sub_article_xml(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(
            xml_root, xml_file_path, version_doi, doctype_dict, processing_instructions
        )

        self.statuses["modify_xml"] = True

        # upload the XML to the bucket
        self.logger.info(
            "%s, updating transformed XML to %s"
            % (self.name, xml_storage_resource_origin)
        )
        storage.set_resource_from_filename(xml_storage_resource_origin, xml_file_path)

        # upload manifest to the bucket
        if self.statuses.get("modify_manifest_xml"):
            self.logger.info(
                "%s, updating manifest XML to %s"
                % (self.name, manifest_storage_resource_origin)
            )
            storage.set_resource_from_filename(
                manifest_storage_resource_origin, manifest_xml_file_path
            )

        self.statuses["upload_xml"] = True

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        self.end_cleaner_log(session)

        # Clean up disk
        self.clean_tmp_dir()

        return True


def find_sub_article_tags(xml_file_path):
    "get the sub-article tags from an XML file"
    root = cleaner.parse_article_xml(xml_file_path)
    tags = []
    # find tags in the XML
    for sub_article_tag in root.findall(".//sub-article"):
        tags.append(sub_article_tag)
    return tags


def find_graphic_tags(parent):
    "look for graphic tags inside the parent tag"
    if parent is not None:
        return parent.findall(".//graphic")
    return []


def find_inline_graphic_tags(parent):
    "look for inline-graphic tags inside the parent tag"
    if parent is not None:
        return parent.findall(".//inline-graphic")
    return []


def remove_sub_article_tags(tag):
    "remove sub-article tags from an XML file"
    # find tags in the XML
    for parent in tag.findall(".//sub-article/.."):
        for sub_article_tag in parent.findall("sub-article"):
            parent.remove(sub_article_tag)
