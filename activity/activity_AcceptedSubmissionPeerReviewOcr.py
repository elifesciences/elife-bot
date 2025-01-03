import os
import json
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider import article_processing, cleaner, ocr
from activity.objects import AcceptedBaseActivity


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
        resource_prefix = self.accepted_expanded_resource_prefix(expanded_folder)

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

        # search XML file for inline graphic tags or graphic tags in table-wrap
        inline_graphic_tags = cleaner.inline_graphic_tags(xml_file_path)
        table_wrap_graphic_tags = cleaner.table_wrap_graphic_tags(xml_file_path)

        # continue only if there are tags found
        if inline_graphic_tags or table_wrap_graphic_tags:
            self.statuses["hrefs"] = True
        else:
            self.logger.info(
                "%s, no inline-graphic or table-wrap graphic tags in %s"
                % (self.name, input_filename)
            )
            self.end_cleaner_log(session)
            return True

        xml_root = cleaner.parse_article_xml(xml_file_path)

        # convert inline-graphic files to maths formulae
        # download inline graphic files from the bucket
        inline_graphic_file_to_path_map = self.download_graphics(
            inline_graphic_tags, files, storage, asset_file_name_map
        )
        self.logger.info(
            "%s, downloaded inline-graphic files %s for %s"
            % (self.name, list(inline_graphic_file_to_path_map.keys()), input_filename)
        )
        file_to_approved_math_data_map = self.process_inline_graphics(
            xml_root,
            inline_graphic_file_to_path_map,
            input_filename,
        )

        # convert table-wrap graphic to table
        # download graphic files from the bucket
        graphic_file_to_path_map = self.download_graphics(
            table_wrap_graphic_tags, files, storage, asset_file_name_map
        )
        self.logger.info(
            "%s, downloaded table-wrap graphic files %s for %s"
            % (self.name, list(graphic_file_to_path_map.keys()), input_filename)
        )
        file_to_approved_table_data_map = self.process_table_wrap_graphics(
            xml_root,
            graphic_file_to_path_map,
            input_filename,
        )

        # remove converted files from the XML and bucket
        approved_file_name_list = list(file_to_approved_math_data_map.keys()) + list(
            file_to_approved_table_data_map.keys()
        )

        if self.statuses["modify_xml"]:
            # remove file tags from the XML
            self.remove_file_tags(xml_root, approved_file_name_list, input_filename)
            # delete converted graphic files from the expanded folder
            self.delete_expanded_folder_files(
                asset_file_name_map, resource_prefix, approved_file_name_list, storage
            )

        # write the XML root to disk
        cleaner.write_xml_file(xml_root, xml_file_path, input_filename)

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

    def download_graphics(self, tags, files, storage, asset_file_name_map):
        # download each image file to disk
        hrefs = []
        for tag in tags:
            href = cleaner.tag_xlink_href(tag)
            hrefs.append(href)

        image_files = [
            file_detail
            for file_detail in files
            if file_detail.get("upload_file_nm") in hrefs
        ]

        cleaner.download_asset_files_from_bucket(
            storage,
            image_files,
            asset_file_name_map,
            self.directories.get("TEMP_DIR"),
            self.logger,
        )

        # create a map of upload_file_nm to local file path
        file_to_path_map = {}
        for file_detail in image_files:
            for asset_key, asset_path in asset_file_name_map.items():
                if file_detail.get("upload_file_nm") and asset_key.endswith(
                    file_detail.get("upload_file_nm")
                ):
                    file_to_path_map[file_detail.get("upload_file_nm")] = asset_path
        return file_to_path_map

    def inline_graphics_to_xml(self, xml_root, file_to_data_map, input_filename):
        "convert inline-graphic tags to mathml"
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
        return file_to_approved_math_data_map

    def process_inline_graphics(
        self,
        xml_root,
        inline_graphic_file_to_path_map,
        input_filename,
    ):
        "replace inline-graphic tags with mathml"
        # OCR inline graphics to maths formulae from the external service
        inline_graphic_file_to_data_map = ocr_files(
            inline_graphic_file_to_path_map,
            "math",
            self.settings,
            self.logger,
            input_filename,
        )
        #  detect error or data

        good_file_to_data_map = {}

        for (
            inline_graphic_file_name,
            response_json,
        ) in inline_graphic_file_to_data_map.items():
            if (
                response_json
                and response_json.get("data")
                and [
                    data_row
                    for data_row in response_json.get("data")
                    if data_row.get("type") == "mathml"
                ]
            ):
                self.logger.info(
                    "%s, got mathml data from OCR of %s inline graphic file: %s"
                    % (self.name, input_filename, inline_graphic_file_name)
                )
                # keep this good file data
                good_file_to_data_map[inline_graphic_file_name] = response_json

            elif response_json and response_json.get("error"):
                self.logger.info(
                    (
                        "%s, got an error in the response "
                        "when getting mathml data from OCR of %s inline graphic file: %s"
                    )
                    % (self.name, input_filename, inline_graphic_file_name)
                )

            else:
                self.logger.info(
                    (
                        "%s, got unrecognised response JSON "
                        "when getting mathml data from OCR of %s inline graphic file: %s"
                    )
                    % (self.name, input_filename, inline_graphic_file_name)
                )

        file_to_approved_math_data_map = self.inline_graphics_to_xml(
            xml_root, good_file_to_data_map, input_filename
        )
        return file_to_approved_math_data_map

    def table_graphics_to_xml(self, xml_root, file_to_data_map, input_filename):
        "convert graphic tags to mathml"
        # a map of which files to change to math equations
        file_to_approved_table_data_map = {
            key: value
            for key, value in file_to_data_map.items()
            if value and value.get("data")
        }

        # replace graphic tags with table XML
        transform_table_graphic_tags(
            xml_root, file_to_approved_table_data_map, self.logger, input_filename
        )

        # for each graphic replaced, remove the file tag
        if file_to_approved_table_data_map:
            file_name_list = file_to_approved_table_data_map.keys()
            self.statuses["modify_xml"] = self.remove_file_tags(
                xml_root, file_name_list, input_filename
            )

        return file_to_approved_table_data_map

    def process_table_wrap_graphics(
        self,
        xml_root,
        graphic_file_to_path_map,
        input_filename,
    ):
        "convert table-wrap graphic tags to table XML"
        # OCR inline graphics to table data from the external service
        graphic_file_to_data_map = ocr_files(
            graphic_file_to_path_map,
            "table",
            self.settings,
            self.logger,
            input_filename,
        )

        good_graphic_file_to_data_map = {}

        for graphic_file_name, response_json in graphic_file_to_data_map.items():
            if (
                response_json
                and response_json.get("data")
                and [
                    data_row
                    for data_row in response_json.get("data")
                    if data_row.get("type") == "tsv"
                ]
            ):
                self.logger.info(
                    "%s, got TSV data from OCR of %s graphic file: %s"
                    % (self.name, input_filename, graphic_file_name)
                )
                # keep this good file data
                good_graphic_file_to_data_map[graphic_file_name] = response_json

            elif response_json and response_json.get("error"):
                self.logger.info(
                    (
                        "%s, got an error in the response "
                        "when getting TSV data from OCR of %s graphic file: %s"
                    )
                    % (self.name, input_filename, graphic_file_name)
                )

            else:
                self.logger.info(
                    (
                        "%s, got unrecognised response JSON "
                        "when getting TSV data from OCR of %s graphic file: %s"
                    )
                    % (self.name, input_filename, graphic_file_name)
                )

        # only add good files which returned TSV data
        file_to_approved_math_data_map = self.table_graphics_to_xml(
            xml_root, good_graphic_file_to_data_map, input_filename
        )
        return file_to_approved_math_data_map


def ocr_files(file_to_path_map, options_type, settings, logger, identifier):
    "post request to an endpoint for each file and return data"
    file_to_data_map = {}
    for file_name, file_path in file_to_path_map.items():
        logger.info(
            "OCR file from %s: file_name %s, file_path %s"
            % (identifier, file_name, file_path)
        )
        try:
            if options_type == "table":
                response = ocr.mathpix_table_post_request(
                    url=settings.mathpix_endpoint,
                    app_id=settings.mathpix_app_id,
                    app_key=settings.mathpix_app_key,
                    file_path=file_path,
                )
            else:
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

        logger.info(
            "JSON response from Mathpix for %s, file_name %s, file_path %s: '%s'"
            % (identifier, file_name, file_path, json.dumps(response_json, indent=4))
        )

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


def transform_table_graphic_tags(xml_root, file_to_table_data_map, logger, identifier):
    "replace graphic tags with table XML"
    for graphic_tag_parent in xml_root.iterfind(".//graphic/.."):
        for tag_index, graphic_tag in enumerate(graphic_tag_parent.iterfind("*")):
            if graphic_tag.tag == "graphic":
                href = cleaner.tag_xlink_href(graphic_tag)
                if href in file_to_table_data_map.keys():
                    # convert TSV to XML, then replace table tag
                    table_data = file_to_table_data_map.get(href).get("data")
                    tsv_string = None
                    for table_data_row in table_data:
                        if table_data_row.get("type") == "tsv":
                            tsv_string = table_data_row.get("value")
                            break
                    table_rows = None
                    if tsv_string:
                        table_rows = cleaner.tsv_to_list(tsv_string)
                    else:
                        log_message = (
                            "transform_table_graphic_tags found no tsv_string"
                            " for href %s in file %s"
                        ) % (
                            href,
                            identifier,
                        )
                        logger.info(log_message)
                        continue
                    # populate a table tag
                    table_tag = None
                    if table_rows:
                        table_tag = cleaner.list_to_table_xml(table_rows)
                    # replace the grpahic tag with the table tag
                    if table_tag is not None:
                        graphic_tag_parent.insert(tag_index, table_tag)
                        graphic_tag_parent.remove(graphic_tag)
