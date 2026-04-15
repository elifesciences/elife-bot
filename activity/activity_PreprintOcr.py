import os
import json
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import ParseError
from elifetools import xmlio
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import cleaner, ocr
from activity.objects import MecaBaseActivity


class activity_PreprintOcr(MecaBaseActivity):
    "PreprintOcr activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_PreprintOcr, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "PreprintOcr"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Transform preprint images by OCR into XML."

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {
            "download": None,
            "xml_root": None,
            "tags_found": None,
            "modify_xml": None,
            "upload": None,
        }

    def do_activity(self, data=None):
        """
        Activity, do the work
        """

        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        # first check if there is an endpoint in the settings specified
        if not hasattr(self.settings, "mathpix_endpoint"):
            self.logger.info(
                "No mathpix_endpoint in settings, skipping %s." % self.name
            )
            return self.ACTIVITY_SUCCESS
        if not self.settings.mathpix_endpoint:
            self.logger.info(
                "mathpix_endpoint in settings is blank, skipping %s." % self.name
            )
            return self.ACTIVITY_SUCCESS

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
        xml_file_path = os.path.join(
            self.directories.get("INPUT_DIR"), article_xml_path
        )

        # create folders if they do not exist
        os.makedirs(os.path.dirname(xml_file_path), exist_ok=True)

        orig_resource = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )

        # download XML from the bucket folder
        storage_resource_origin = orig_resource + "/" + article_xml_path
        self.logger.info(
            "%s, downloading %s to %s"
            % (self.name, storage_resource_origin, xml_file_path)
        )
        with open(xml_file_path, "wb") as open_file:
            storage.get_resource_to_file(storage_resource_origin, open_file)
        self.statuses["download"] = True

        # parse the XML root and doctype
        xml_root, doctype_dict, processing_instructions = xmlio.parse(
            xml_file_path,
            return_doctype_dict=True,
            return_processing_instructions=True,
            insert_pis=True,
            insert_comments=True,
        )
        self.statuses["xml_root"] = True

        # assess preprint XML for formula images to convert
        try:
            disp_formula_tags = find_disp_formula_tags(xml_root)
            inline_formula_tags = find_inline_formula_tags(xml_root)
        except Exception as exception:
            self.logger.exception(
                "%s, exception raised finding disp-formula and inline-formula tags for %s: %s"
                % (self.name, version_doi, str(exception)),
            )
            return True

        if not (disp_formula_tags or inline_formula_tags):
            self.logger.info(
                "%s, no applicable disp-formula or inline-formula tags to OCR for %s"
                % (self.name, version_doi)
            )
            # Clean up disk
            self.clean_tmp_dir()
            return True

        self.statuses["tags_found"] = True

        # download manifest.xml file
        expanded_resource_prefix = (
            self.settings.storage_provider
            + "://"
            + self.settings.bot_bucket
            + "/"
            + expanded_folder
        )
        self.logger.info(
            "%s, downloading manifest.xml for %s from %s"
            % (self.name, version_doi, expanded_resource_prefix)
        )

        (
            manifest_xml_file_path,
            manifest_storage_resource_origin,
        ) = self.download_manifest(storage, expanded_resource_prefix)
        with open(manifest_xml_file_path, "r", encoding="utf-8") as open_file:
            manifest_content = open_file.read()
        manifest_root = ElementTree.fromstring(manifest_content)

        # get a list of images to OCR from XML
        graphic_image_names = []
        if disp_formula_tags:
            for tag in disp_formula_tags:
                graphic_image_names.append(
                    tag.find(".//graphic").get("{http://www.w3.org/1999/xlink}href")
                )
        self.logger.info(
            "%s, in %s found graphic_image_names %s"
            % (self.name, version_doi, graphic_image_names)
        )
        inline_graphic_image_names = []
        if inline_formula_tags:
            for tag in inline_formula_tags:
                inline_graphic_image_names.append(
                    tag.find(".//inline-graphic").get(
                        "{http://www.w3.org/1999/xlink}href"
                    )
                )
        self.logger.info(
            "%s, in %s found inline_graphic_image_names %s"
            % (self.name, version_doi, inline_graphic_image_names)
        )

        # get file names from the manifest
        (
            graphic_file_to_path_map,
            inline_graphic_file_to_path_map,
        ) = file_paths_from_manifest(
            manifest_root,
            graphic_image_names,
            inline_graphic_image_names,
            version_doi,
            self.name,
            self.logger,
        )
        self.logger.info(
            "%s, graphic_file_to_path_map for %s: %s"
            % (self.name, version_doi, graphic_file_to_path_map)
        )
        self.logger.info(
            "%s, inline_graphic_file_to_path_map for %s: %s"
            % (self.name, version_doi, inline_graphic_file_to_path_map)
        )

        # download image files from S3
        downloaded_graphic_file_to_path_map = download_graphics(
            storage,
            expanded_resource_prefix,
            graphic_file_to_path_map,
            self.directories.get("TEMP_DIR"),
            self.name,
            self.logger,
        )
        self.logger.info(
            "%s, downloaded graphic files %s for %s"
            % (self.name, list(downloaded_graphic_file_to_path_map.keys()), version_doi)
        )
        downloaded_inline_graphic_file_to_path_map = download_graphics(
            storage,
            expanded_resource_prefix,
            inline_graphic_file_to_path_map,
            self.directories.get("TEMP_DIR"),
            self.name,
            self.logger,
        )
        self.logger.info(
            "%s, downloaded inline-graphic files %s for %s"
            % (
                self.name,
                list(downloaded_inline_graphic_file_to_path_map.keys()),
                version_doi,
            )
        )

        try:
            #  OCR each disp-formula graphic file
            self.logger.info(
                "%s, starting OCR of graphic_file_to_data_map for %s"
                % (self.name, version_doi)
            )
            graphic_file_to_data_map = ocr.ocr_files(
                downloaded_graphic_file_to_path_map,
                "disp-formula",
                "preprint",
                self.settings,
                self.name,
                self.logger,
                version_doi,
            )

            # OCR each inline-graphic file
            self.logger.info(
                "%s, starting OCR of inline_graphic_file_to_data_map for %s"
                % (self.name, version_doi)
            )
            inline_graphic_file_to_data_map = ocr.ocr_files(
                downloaded_inline_graphic_file_to_path_map,
                "math",
                "preprint",
                self.settings,
                self.name,
                self.logger,
                version_doi,
            )
        except Exception as exception:
            self.logger.exception(
                "%s, exception raised in ocr_files for %s: %s"
                % (self.name, version_doi, str(exception)),
            )
            return True

        try:
            # rewrite preprint XML with mathml and other data
            self.logger.info(
                "%s, rewriting disp-formula tags for %s" % (self.name, version_doi)
            )
            rewrite_disp_formula_tags(
                disp_formula_tags, graphic_file_to_data_map, self.logger
            )
            self.logger.info(
                "%s, rewriting inline-formula tags for %s" % (self.name, version_doi)
            )
            rewrite_inline_formula_tags(
                inline_formula_tags, inline_graphic_file_to_data_map, self.logger
            )
            self.logger.info(
                "%s, finished modifying XML for %s" % (self.name, version_doi)
            )
            self.statuses["modify_xml"] = True
        except Exception as exception:
            self.logger.exception(
                "%s, exception raised in rewriting XML for %s: %s"
                % (self.name, version_doi, str(exception)),
            )
            return True

        # make XML pretty
        cleaner.pretty_formula_xml(xml_root)

        # write the XML root to disk
        cleaner.write_xml_file(
            xml_root, xml_file_path, version_doi, doctype_dict, processing_instructions
        )

        # upload preprint XML to bucket expanded folder
        s3_resource = orig_resource + "/" + article_xml_path
        self.logger.info("%s, updating modified XML to %s" % (self.name, s3_resource))
        storage.set_resource_from_filename(s3_resource, xml_file_path)
        self.statuses["upload"] = True

        self.end_cleaner_log(session)

        self.logger.info("%s statuses: %s" % (self.name, self.statuses))

        # Clean up disk
        self.clean_tmp_dir()

        return True


def file_paths_from_manifest(
    manifest_root,
    graphic_image_names,
    inline_graphic_image_names,
    version_doi,
    caller_name,
    logger,
):
    graphic_file_to_path_map = {}
    inline_graphic_file_to_path_map = {}
    for item_tag in manifest_root.findall(".//{http://manuscriptexchange.org}item"):
        instance_tag = item_tag.find(".//{http://manuscriptexchange.org}instance")
        if instance_tag is None:
            continue
        href = instance_tag.get("href")
        if href:
            graphic_file = href.rsplit("/", 1)[-1]
            if graphic_file in graphic_image_names:
                logger.info(
                    "%s, manifest file %s matched in graphic_image_names for %s"
                    % (caller_name, graphic_file, version_doi)
                )
                graphic_file_to_path_map[graphic_file] = href
            elif graphic_file in inline_graphic_image_names:
                logger.info(
                    "%s, manifest file %s matched in inline_graphic_image_names for %s"
                    % (caller_name, graphic_file, version_doi)
                )
                inline_graphic_file_to_path_map[graphic_file] = href
    return graphic_file_to_path_map, inline_graphic_file_to_path_map


def download_graphics(
    storage, resource_prefix, file_name_map, to_dir, caller_name, logger
):
    # download each image file to disk
    downloaded_file_name_map = {}
    for file_name, file_path in file_name_map.items():
        local_file_path = os.path.join(to_dir, file_path)

        # create folders if they do not exist
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        storage_resource_origin = resource_prefix + "/" + file_path
        logger.info(
            "%s, downloading %s to %s"
            % (caller_name, storage_resource_origin, local_file_path)
        )
        try:
            with open(local_file_path, "wb") as open_file:
                storage.get_resource_to_file(storage_resource_origin, open_file)
        except Exception as exception:
            logger.exception(
                "%s, exception downloading storage_resource_origin %s: %s"
                % (caller_name, file_name, str(exception)),
            )
            continue
        downloaded_file_name_map[file_name] = local_file_path
    return downloaded_file_name_map


def find_ocr_tags(xml_root, tag_name):
    "find tags in the XML root of tag tag_name which do not have mml:math tags"
    tags = []
    for tag in xml_root.findall(".//%s" % tag_name):
        if not list(tag.iterfind(".//{http://www.w3.org/1998/Math/MathML}math")):
            tags.append(tag)
    return tags


def find_disp_formula_tags(xml_root):
    "find disp-formula tags in the XML root which are suitable to OCR"
    return find_ocr_tags(xml_root, "disp-formula")


def find_inline_formula_tags(xml_root):
    "find inline-formula tags in the XML root which are suitable to OCR"
    return find_ocr_tags(xml_root, "inline-formula")


def rewrite_formula_tags(formula_tags, file_to_data_map, tag_type, logger):
    if tag_type == "disp-formula":
        graphic_tag_type = "graphic"
    elif tag_type == "inline-formula":
        graphic_tag_type = "inline-graphic"
    for tag in formula_tags:
        graphic_tag = tag.find(".//%s" % graphic_tag_type)
        if graphic_tag is None or not graphic_tag.get(
            "{http://www.w3.org/1999/xlink}href"
        ):
            logger.info(
                "no %s tag found in %s" % (graphic_tag_type, ElementTree.tostring(tag))
            )
            continue
        file_href = graphic_tag.get("{http://www.w3.org/1999/xlink}href")
        # optionally use an existing alternatives tag
        alternatives_tag = tag.find(".//alternatives")
        insert_alternatives_tag = False
        if file_href:
            #  create alternatives tag if not already found
            if alternatives_tag is None:
                alternatives_tag = Element("alternatives")
                insert_alternatives_tag = True

            mathml_data, latex_data = None, None
            response_data = file_to_data_map.get(file_href)
            if response_data:
                math_data = response_data.get("data")
                mathml_data, latex_data = ocr.math_data_parts(math_data)
            if not mathml_data:
                logger.info("no mathml data found for file %s" % file_href)
                continue
            math_tag = None
            if mathml_data and mathml_data.get("value"):
                # first parse the mathml
                try:
                    math_tag = ElementTree.fromstring(mathml_data.get("value"))
                except ParseError:
                    log_message = (
                        "rewrite %s tags XML ParseError exception"
                        " parsing XML %s for file %s"
                    ) % (
                        tag_type,
                        mathml_data.get("value"),
                        file_href,
                    )
                    logger.exception(log_message)
                    continue
            if math_tag is not None:
                alternatives_tag.append(math_tag)
            # add latex if available
            if latex_data and latex_data.get("value"):
                math_tag.set("alttext", latex_data.get("value"))
            alternatives_tag.append(graphic_tag)
            tag.remove(graphic_tag)
            if insert_alternatives_tag:
                tag.insert(0, alternatives_tag)


def rewrite_disp_formula_tags(disp_formula_tags, file_to_data_map, logger):
    "add mathml to disp-formula tags"
    rewrite_formula_tags(disp_formula_tags, file_to_data_map, "disp-formula", logger)


def rewrite_inline_formula_tags(inline_formula_tags, file_to_data_map, logger):
    "add mathml to inline-formula tags"
    rewrite_formula_tags(
        inline_formula_tags, file_to_data_map, "inline-formula", logger
    )
