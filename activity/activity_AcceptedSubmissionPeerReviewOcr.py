import os
import json
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner, ocr
from activity.objects import AcceptedBaseActivity


REPAIR_XML = False


class activity_AcceptedSubmissionPeerReviewOcr(AcceptedBaseActivity):
    "AcceptedSubmissionPeerReviewOcr activity"

    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_AcceptedSubmissionPeerReviewOcr, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "AcceptedSubmissionPeerReviewOcr"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 30
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Transform peer review inline graphic images into "
            "maths equations and tables."
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"hrefs": None, "modify_xml": None, "rename_files": None}

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

        # get list of files from the article XML
        try:
            files = cleaner.file_list(xml_file_path)
        except ParseError:
            log_message = (
                "%s, XML ParseError exception in cleaner.file_list"
                " parsing XML file %s for file %s"
            ) % (
                self.name,
                article_processing.file_name_from_name(xml_file_path),
                input_filename,
            )
            self.logger.exception(log_message)
            cleaner.LOGGER.exception(log_message)
            files = []
            return True

        self.logger.info("%s, files: %s" % (self.name, files))

        # search XML file for graphic tags
        if not cleaner.inline_graphic_tags(xml_file_path):
            self.logger.info(
                "%s, no inline-graphic tags in %s" % (self.name, input_filename)
            )
            self.end_cleaner_log(session)
            return True

        self.statuses["hrefs"] = True

        xml_root = cleaner.parse_article_xml(xml_file_path)

        # download each inline graphic image to disk
        inline_graphic_hrefs = []
        for inline_graphic_tag in xml_root.iterfind(".//inline-graphic"):
            href = cleaner.tag_xlink_href(inline_graphic_tag)
            inline_graphic_hrefs.append(href)

        inline_graphic_files = [
            file_detail
            for file_detail in files
            if file_detail.get("upload_file_nm") in inline_graphic_hrefs
        ]

        cleaner.download_asset_files_from_bucket(
            storage,
            inline_graphic_files,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # create a map of upload_file_nm to local file path
        file_to_path_map = {}
        for file_detail in inline_graphic_files:
            for asset_key, asset_path in asset_file_name_map.items():
                if file_detail.get("upload_file_nm") and asset_key.endswith(
                    file_detail.get("upload_file_nm")
                ):
                    file_to_path_map[file_detail.get("upload_file_nm")] = asset_path

        # request math formula from the external service
        file_to_data_map = ocr_files(
            file_to_path_map, self.settings, self.logger, input_filename
        )

        # a map of which files to change to math equations
        file_to_approved_math_data_map = {
            key: value for key, value in file_to_data_map.items() if value.get("data")
        }

        # replace inline-graphic tags with maths formulae
        transform_inline_graphic_tags(
            xml_root, file_to_approved_math_data_map, self.logger, input_filename
        )

        # for each inline graphic replaced, remove the file tag
        if file_to_approved_math_data_map:
            file_name_list = file_to_approved_math_data_map.keys()
            self.statuses["modify_xml"] = self.remove_file_tags(
                xml_root, file_name_list, input_filename
            )

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

        # for each inline-graphic replaced, delete it from the expanded folder
        if self.statuses["modify_xml"]:
            file_name_list = file_to_approved_math_data_map.keys()
            self.delete_expanded_folder_files(
                asset_file_name_map, expanded_folder, file_name_list, storage
            )

        # upload the XML to the bucket
        if self.statuses["modify_xml"]:
            self.upload_xml_file_to_bucket(
                asset_file_name_map, expanded_folder, storage
            )

        self.end_cleaner_log(session)

        self.log_statuses(input_filename)

        # Clean up disk
        self.clean_tmp_dir()

        return True


def ocr_files(file_to_path_map, settings, logger, identifier):
    "post request to an endpoint for each file and return data"
    file_to_data_map = {}
    for file_name, file_path in file_to_path_map.items():
        logger.info(
            "OCR file from %s: file_name %s, file_path %s"
            % (identifier, file_name, file_path)
        )

        try:
            response = ocr.mathpix_post_request(
                url=settings.mathpix_endpoint,
                app_id=settings.mathpix_app_id,
                app_key=settings.mathpix_app_key,
                file_path=file_path,
            )
        except Exception as exception:
            logger.exception(
                "Exception posting to Mathpix API endpoint, file_name %s: %s"
                % (file_name, str(exception)),
            )
            continue

        # get the response.json and use that
        response_json = response.json()

        # format response data
        file_to_data_map[file_name] = response_json
    return file_to_data_map


def math_data_parts(math_data):
    "from a list math_data find the different types of data"
    mathml_data = None
    latex_data = None
    for math_data_row in math_data:
        if math_data_row.get("type") == "mathml":
            mathml_data = math_data_row
            continue
        if math_data_row.get("type") == "latex":
            latex_data = math_data_row
    return mathml_data, latex_data


def transform_inline_graphic_tags(xml_root, file_to_math_data_map, logger, identifier):
    "replace inline-graphic tags with maths formulae"
    # for each inline graphic with a math formula, replace the XML tag
    for parent_tag in xml_root.iterfind(".//inline-graphic/.."):
        # figure out whether to use inline-formula tag or disp-formula tag
        formula_tag_name = "inline-formula"
        if cleaner.is_p_inline_graphic(
            tag=parent_tag,
            sub_article_id=None,
            p_tag_index=None,
            identifier=identifier,
        ):
            formula_tag_name = "disp-formula"

        # convert each inline-graphic tag
        for inline_graphic_tag in parent_tag.iterfind("inline-graphic"):
            href = cleaner.tag_xlink_href(inline_graphic_tag)
            if href in file_to_math_data_map.keys():
                math_data = file_to_math_data_map.get(href).get("data")
                mathml_data, latex_data = math_data_parts(math_data)

                if mathml_data and mathml_data.get("value"):
                    # first parse the mathml
                    try:
                        math_tag = ElementTree.fromstring(mathml_data.get("value"))
                    except ParseError:
                        log_message = (
                            "transform_inline_graphic_tags XML ParseError exception"
                            " parsing XML %s for file %s"
                        ) % (
                            mathml_data.get("value"),
                            identifier,
                        )
                        logger.exception(log_message)
                        continue

                    # convert inline-graphic tag
                    inline_graphic_tag.tag = formula_tag_name
                    cleaner.remove_tag_attributes(inline_graphic_tag)
                    # add <math> tag
                    inline_graphic_tag.append(math_tag)
                    # add latex if available
                    if latex_data and latex_data.get("value"):
                        math_tag.set("alttext", latex_data.get("value"))
