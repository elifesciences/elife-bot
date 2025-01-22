import os
import json
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, peer_review, meca
from activity.objects import MecaBaseActivity


class activity_MecaPeerReviewEquations(MecaBaseActivity):
    "MecaPeerReviewEquations activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaPeerReviewEquations, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaPeerReviewEquations"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Transform certain peer review inline graphic image content into "
            "equations for MECA XML."
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
            "modify_manifest_xml": None,
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

        # search XML file for graphic tags
        inline_graphic_tags = cleaner.inline_graphic_tags(xml_file_path)
        if not inline_graphic_tags:
            self.logger.info(
                "%s, no inline-graphic tags in %s" % (self.name, version_doi)
            )
            self.end_cleaner_log(session)
            return True

        self.statuses["hrefs"] = True

        content_subfolder = meca.meca_content_folder(article_xml_path)

        xml_root = cleaner.parse_article_xml(xml_file_path)

        # transform inline-graphic into disp-formula
        disp_file_transformations = peer_review.generate_equation_file_transformations(
            xml_root,
            identifier=version_doi,
            caller_name=self.name,
            logger=self.logger,
        )

        self.logger.info(
            "%s, %s disp_file_transformations: %s"
            % (self.name, version_doi, disp_file_transformations)
        )

        # transform inline-graphic into inline-formula, and add them to file_transformationsn
        inline_file_transformations = (
            peer_review.generate_inline_equation_file_transformations(
                xml_root,
                identifier=version_doi,
                caller_name=self.name,
                logger=self.logger,
            )
        )

        self.logger.info(
            "%s, %s inline_file_transformations: %s"
            % (self.name, version_doi, inline_file_transformations)
        )

        file_transformations = disp_file_transformations + inline_file_transformations

        if not file_transformations:
            self.logger.info(
                "%s, no file_transformations in %s" % (self.name, version_doi)
            )
            self.logger.info("%s statuses: %s" % (self.name, self.statuses))
            self.end_cleaner_log(session)
            return True

        self.logger.info(
            "%s, total file_transformations: %s"
            % (self.name, len(file_transformations))
        )
        self.logger.info(
            "%s, file_transformations: %s" % (self.name, file_transformations)
        )

        self.statuses["modify_xml"] = True

        cleaner.pretty_sub_article_xml(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, version_doi)

        # find duplicates in file_transformations
        (
            copy_file_transformations,
            rename_file_transformations,
        ) = peer_review.filter_transformations(file_transformations)

        self.logger.info(
            "%s, %s copy_file_transformations: %s"
            % (self.name, version_doi, copy_file_transformations)
        )

        self.logger.info(
            "%s, %s rename_file_transformations: %s"
            % (self.name, version_doi, rename_file_transformations)
        )

        # rewrite the XML file with the renamed files
        if file_transformations:
            # download manifest XML file
            (
                manifest_xml_file_path,
                manifest_storage_resource_origin,
            ) = self.download_manifest(storage, resource_prefix)

            # collect details for formula / equations
            rename_file_detail_list = collect_formula_file_details(
                xml_root, rename_file_transformations, content_subfolder
            )
            # rewrite item tags in manifest file
            meca.rewrite_item_tags(
                manifest_xml_file_path,
                rename_file_detail_list,
                version_doi,
                self.name,
                self.logger,
            )

            copy_file_detail_list = collect_formula_file_details(
                xml_root, copy_file_transformations, content_subfolder
            )

            # add item tags for duplicate files
            cleaner.add_item_tags_to_manifest_xml(
                manifest_xml_file_path, copy_file_detail_list, version_doi
            )

            # make manifest XML more pretty with added new line characters
            cleaner.pretty_manifest_xml(manifest_xml_file_path, version_doi)

            self.statuses["modify_manifest_xml"] = True

        # collect asset file name paths for s3 object copying routine
        asset_file_name_map = {}
        for detail in rename_file_detail_list + copy_file_detail_list:
            if detail.get("from_href"):
                asset_file_name_map[detail.get("from_href")] = detail.get("from_href")

        self.logger.info(
            "%s, %s asset_file_name_map: %s"
            % (self.name, version_doi, asset_file_name_map)
        )

        # copy duplicate files in the expanded folder
        self.meca_copy_expanded_folder_files(
            version_doi,
            asset_file_name_map,
            resource_prefix,
            copy_file_transformations,
            storage,
        )

        # rename the files in the expanded folder
        self.meca_rename_expanded_folder_files(
            version_doi,
            asset_file_name_map,
            resource_prefix,
            rename_file_transformations,
            storage,
        )

        self.statuses["rename_files"] = True

        # upload the XML to the bucket
        self.logger.info(
            "%s, updating transformed XML to %s"
            % (self.name, xml_storage_resource_origin)
        )
        storage.set_resource_from_filename(xml_storage_resource_origin, xml_file_path)

        # upload manifest to the bucket
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


def collect_formula_file_details(root, file_transformations, content_subfolder):
    "file transformation details of block and inline equation graphic files"
    file_detail_list = collect_disp_formula_file_details(
        root, file_transformations, content_subfolder
    )
    file_detail_list += collect_inline_formula_file_details(
        root, file_transformations, content_subfolder
    )
    return file_detail_list


def collect_disp_formula_file_details(root, file_transformations, content_subfolder):
    "disp-formula file details for use in XML from the file transformation data"
    variant_data = {
        "parent_tag_name": "disp-formula",
        "graphic_tag_name": "graphic",
        "file_type": "equation",
    }
    return meca.collect_transformation_file_details(
        variant_data, root, file_transformations, content_subfolder
    )


def collect_inline_formula_file_details(root, file_transformations, content_subfolder):
    "inline-formula file details for use in XML from the file transformation data"
    variant_data = {
        "parent_tag_name": "inline-formula",
        "graphic_tag_name": "inline-graphic",
        "file_type": "equation",
    }
    return meca.collect_transformation_file_details(
        variant_data, root, file_transformations, content_subfolder
    )
