# coding=utf-8

import copy
import importlib
import os
import re
import glob
import shutil
import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from mock import Mock, patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner, ocr
import activity.activity_PreprintOcr as activity_module
from activity.activity_PreprintOcr import (
    activity_PreprintOcr as activity_object,
)
import tests.test_data as test_case_data
from tests.activity.classes_mock import (
    FakeLogger,
    FakeResponse,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


def input_data(file_name_to_change=""):
    activity_data = test_case_data.ingest_accepted_submission_data
    activity_data["file_name"] = file_name_to_change
    return activity_data


SESSION_DICT = test_activity_data.post_preprint_publication_session_example()


EXAMPLE_DISP_FORMULA_RESPONSE_JSON = {
    "request_id": "2023_06_20_85e56a13304ac2be4063g",
    "version": "RSK-M115",
    "image_width": 171,
    "image_height": 64,
    "is_printed": True,
    "is_handwritten": False,
    "auto_rotate_confidence": 0,
    "auto_rotate_degrees": 0,
    "confidence": 0.8816322172060609,
    "confidence_rate": 0.8816322172060609,
    "latex_styled": "\\tau \\frac{d \\boldsymbol{a}}{d t}=\\boldsymbol{C a}+\\boldsymbol{b}",
    "text": "\\tag{A.1}\n$\\tau \\frac{d \\boldsymbol{a}}{d t}=\\boldsymbol{C a}+\\boldsymbol{b}$",
    "data": [
        {
            "type": "mathml",
            "value": '<math xmlns="http://www.w3.org/1998/Math/MathML">\n  <mtable displaystyle="true">\n    <mlabeledtr>\n      <mtd id="mjx-eqn:A.1">\n        <mtext>(A.1)</mtext>\n      </mtd>\n      <mtd>\n        <mi>τ</mi>\n        <mfrac>\n          <mrow>\n            <mi>d</mi>\n            <mi mathvariant="bold-italic">a</mi>\n          </mrow>\n          <mrow>\n            <mi>d</mi>\n            <mi>t</mi>\n          </mrow>\n        </mfrac>\n        <mo>=</mo>\n        <mi mathvariant="bold-italic">C</mi>\n        <mi mathvariant="bold-italic">a</mi>\n        <mo>+</mo>\n        <mi mathvariant="bold-italic">b</mi>\n      </mtd>\n    </mlabeledtr>\n  </mtable>\n</math>',
        },
        {
            "type": "latex",
            "value": "\\tau \\frac{d \\boldsymbol{a}}{d t}=\\boldsymbol{C a}+\\boldsymbol{b}",
        },
    ],
}

EQUATION_DATA = test_activity_data.EXAMPLE_OCR_RESPONSE_JSON.get("data")
DISP_FORMULA_EQUATION_DATA = EXAMPLE_DISP_FORMULA_RESPONSE_JSON.get("data")

OCR_FILES_DATA = {
    "681678v1_ueqn1.gif": {
        "data": DISP_FORMULA_EQUATION_DATA,
    },
    "681678v1_ueqn3.gif": {
        "data": [],
    },
    "5681678v1_inline1.gif": {
        "data": EQUATION_DATA,
    },
    "5681678v1_inline2.gif": {
        "data": [],
    },
    "5681678v1_inline3.gif": {
        "error": "formats must be an array",
        "error_info": {
            "id": "opts_expected_array",
            "message": "formats must be an array",
            "option": "formats",
            "type": "string",
        },
    },
}


def mock_mathpix_post_request(
    url=None,
    app_id=None,
    app_key=None,
    file_path=None,
    **kwargs,
):
    "return a FakeResponse containing the response data based on the file_name"
    response = FakeResponse(201)
    file_name = file_path.rsplit(os.sep, 1)[-1]
    if file_name and file_name in OCR_FILES_DATA:
        response.response_json = OCR_FILES_DATA.get(file_name)
    return response


def add_body_article_xml(xml_path, body_xml):
    "add XML to the end of the XML file body tag"
    with open(xml_path, "r", encoding="utf-8") as open_file:
        xml_string = open_file.read()
    with open(xml_path, "w", encoding="utf-8") as open_file:
        xml_string = xml_string.replace("</body>", "%s</body>" % body_xml)
        open_file.write(xml_string)


def add_manifest_xml(manifest_file_path, image_names):
    "add XML to manifest.xml file for image names used in test scenario"
    with open(
        manifest_file_path,
        "r",
        encoding="utf-8",
    ) as open_file:
        manifest_content = open_file.read()
    # add manifest item tags for each image file
    manifest_content = manifest_content.replace(
        "</manifest>",
        "%s</manifest>" % generate_manifest_xml(image_names),
    )
    with open(
        manifest_file_path,
        "w",
        encoding="utf-8",
    ) as open_file:
        open_file.write(manifest_content)


def generate_manifest_xml(image_names):
    "generate item tags to add to a manifest.xml fixture for images added to a MECA fixture"
    if not image_names:
        return ""
    manifest_xml_string = ""
    image_name_match_pattern = re.compile(r"^.*?_(.*)\.(.*)$")
    for image_name in image_names:
        image_matches = image_name_match_pattern.match(image_name)
        if image_matches:
            image_id = image_matches[1]
            image_media_type = image_matches[2]
            image_type = "figure"
            if image_id.startswith("ueqn") or image_id.startswith("inline"):
                image_type = "equation"
            manifest_xml_string += (
                '<item id="%s" type="%s">\n'
                '<instance media-type="image/%s" href="content/%s"/>\n'
                "</item>\n"
            ) % (image_id, image_type, image_media_type, image_name)
    return manifest_xml_string


@ddt
class TestPreprintOcr(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)
        # reload the module which had MagicMock applied to revert the mock
        importlib.reload(ocr)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no formulae",
            "image_names": None,
            "expected_result": True,
            "expected_tags_found_status": None,
            "expected_modify_xml_status": None,
            "expected_upload_status": None,
            "expected_activity_log_contains": [
                (
                    "PreprintOcr, no applicable disp-formula "
                    "or inline-formula tags to OCR for "
                    "10.7554/eLife.95901.2"
                )
            ],
        },
        {
            "comment": "example with disp-formula and inline-formula",
            "additional_xml": (
                "<?fig-width 50%?>\n"
                "<!--test-->\n"
                '<disp-formula id="ueqn1">\n'
                '<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif"/>\n'
                "</disp-formula>\n"
                '<disp-formula id="ueqn2">\n'
                "<alternatives>\n"
                "<mml:math>...</mml:math>\n"
                '<graphic xlink:href="681678v1_ueqn2.gif" mimetype="image" mime-subtype="gif"/>\n'
                "</alternatives>\n"
                "</disp-formula>\n"
                '<disp-formula id="ueqn3">\n'
                '<graphic xlink:href="681678v1_ueqn3.gif" mimetype="image" mime-subtype="gif"/>\n'
                "</disp-formula>\n"
                "<p>Here \n"
                "<inline-formula>\n"
                '<inline-graphic xlink:href="5681678v1_inline1.gif"'
                ' mimetype="image" mime-subtype="gif"/>\n'
                "</inline-formula>\n"
                ", and here \n"
                "<inline-formula>\n"
                '<inline-graphic xlink:href="5681678v1_inline2.gif"'
                ' mimetype="image" mime-subtype="gif"/>\n'
                "</inline-formula>\n"
                ", and also here \n"
                "<inline-formula>\n"
                '<inline-graphic xlink:href="5681678v1_inline3.gif"'
                ' mimetype="image" mime-subtype="gif"/>\n'
                "</inline-formula>\n"
                ".\n"
                "</p>\n"
            ),
            "image_names": [
                "681678v1_ueqn1.gif",
                "681678v1_ueqn2.gif",
                "681678v1_ueqn3.gif",
                "5681678v1_inline1.gif",
                "5681678v1_inline2.gif",
                "5681678v1_inline3.gif",
            ],
            "expected_result": True,
            "expected_tags_found_status": True,
            "expected_modify_xml_status": True,
            "expected_upload_status": True,
            "expected_xml_contains": [
                (
                    '<?xml version="1.0" ?>'
                    "<!DOCTYPE article PUBLIC"
                    ' "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange'
                    ' DTD v1.3 20210610//EN"  "JATS-archivearticle1-mathml3.dtd">'
                    '<article xmlns:mml="http://www.w3.org/1998/Math/MathML"'
                    ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                    ' article-type="research-article" dtd-version="1.3" xml:lang="en">'
                ),
                (
                    "<?fig-width 50%?>\n"
                    "<!--test-->\n"
                    '<disp-formula id="ueqn1">\n<alternatives>\n'
                    '<mml:math alttext="\\tau \\frac{d \\boldsymbol{a}}{d t}='
                    '\\boldsymbol{C a}+\\boldsymbol{b}">\n'
                    '  <mml:mtable displaystyle="true">\n'
                    "    <mml:mlabeledtr>\n"
                    '      <mml:mtd id="mjx-eqn:A.1">\n'
                    "        <mml:mtext>(A.1)</mml:mtext>\n"
                    "      </mml:mtd>\n"
                    "      <mml:mtd>\n"
                    "        <mml:mi>τ</mml:mi>\n"
                ),
                ('<disp-formula id="ueqn2">\n<alternatives>\n<mml:math>...'),
                ('<disp-formula id="ueqn3">\n<graphic xlink:href="681678v1_ueqn3.gif"'),
                (
                    "<inline-formula>\n"
                    "<alternatives>\n"
                    '<mml:math alttext="\\tau \\frac{d \\boldsymbol{a}}{d t}='
                    '\\boldsymbol{C a}+\\boldsymbol{b}">\n'
                    "  <mml:mi>τ</mml:mi>\n"
                    "  <mml:mfrac>\n"
                    "    <mml:mrow>\n"
                    "      <mml:mi>d</mml:mi>\n"
                    '      <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
                    "    </mml:mrow>\n"
                    "    <mml:mrow>\n"
                    "      <mml:mi>d</mml:mi>\n"
                    "      <mml:mi>t</mml:mi>\n"
                    "    </mml:mrow>\n"
                    "  </mml:mfrac>\n"
                    "  <mml:mo>=</mml:mo>\n"
                    '  <mml:mi mathvariant="bold-italic">C</mml:mi>\n'
                    '  <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
                    "  <mml:mo>+</mml:mo>\n"
                    '  <mml:mi mathvariant="bold-italic">b</mml:mi>\n'
                    "</mml:math>\n"
                    '<inline-graphic xlink:href="5681678v1_inline1.gif"'
                    ' mimetype="image" mime-subtype="gif"/>\n'
                    "</alternatives>\n"
                    "</inline-formula>"
                ),
                (
                    "<inline-formula>\n"
                    '<inline-graphic xlink:href="5681678v1_inline2.gif"'
                    ' mimetype="image" mime-subtype="gif"/>\n'
                    "</inline-formula>\n"
                ),
                (
                    "<inline-formula>\n"
                    '<inline-graphic xlink:href="5681678v1_inline3.gif"'
                    ' mimetype="image" mime-subtype="gif"/>\n'
                    "</inline-formula>\n"
                ),
            ],
            "expected_xml_not_contains": [
                ('<disp-formula id="ueqn1">\n' "<graphic"),
            ],
            "expected_activity_log_contains": [
                (
                    "PreprintOcr, updating modified XML to"
                    " s3://bot_bucket/expanded_meca/95901-v2/1ee54f9a-cb28-4c8e-8232-4b317cf4beda"
                    "/expanded_files/content/24301711.xml"
                ),
            ],
            "expected_cleaner_log_contains": [
                (
                    "INFO elifecleaner:transform:write_xml_file: 10.7554/eLife.95901.2"
                    " writing xml to file tmp/"
                )
            ],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        fake_session.return_value = self.session

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                self.session.get_value("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]

        content_folder = os.path.join(
            self.session.get_value("expanded_folder"), "content"
        )

        # add additional image file fixtures
        if test_data.get("image_names"):
            for image_name in test_data.get("image_names"):
                file_path = os.path.join(directory.path, content_folder, image_name)
                shutil.copyfile(
                    "tests/files_source/digests/outbox/99999/digest-99999.jpg",
                    file_path,
                )
                resources.append(os.path.join(content_folder, image_name))

        # write additional XML to the XML file
        if test_data.get("additional_xml"):
            add_body_article_xml(
                destination_path,
                test_data.get("additional_xml"),
            )

        # add manifest XML for image files
        if test_data.get("image_names"):
            manifest_file_path = os.path.join(
                directory.path,
                self.session.get_value("expanded_folder"),
                "manifest.xml",
            )
            add_manifest_xml(manifest_file_path, test_data.get("image_names"))

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        # mock the Mathpix API requests with a mock function
        ocr.mathpix_post_request = Mock(side_effect=mock_mathpix_post_request)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        self.assertEqual(result, test_data.get("expected_result"))

        # assert XML is in input_dir
        input_dir_files = glob.glob(self.activity.directories.get("INPUT_DIR") + "/*/*")
        input_dir_article_xml_path = os.path.join(
            self.activity.directories.get("INPUT_DIR"),
            SESSION_DICT.get("article_xml_path"),
        )
        self.assertTrue(input_dir_article_xml_path in input_dir_files)

        # assertions on XML content
        with open(destination_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()

        self.assertTrue("<article" in xml_content)

        # assertion on XML contents
        if test_data.get("expected_xml_contains") or test_data.get(
            "expected_xml_not_contains"
        ):
            # with open(destination_path, "r", encoding="utf-8") as open_file:
            #     xml_content = open_file.read()
            for fragment in test_data.get("expected_xml_contains", []):
                self.assertTrue(
                    fragment in xml_content,
                    "failed in {comment}, fragment: {fragment}".format(
                        comment=test_data.get("comment"), fragment=fragment
                    ),
                )
            for fragment in test_data.get("expected_xml_not_contains", []):
                self.assertTrue(
                    fragment not in xml_content,
                    "failed in {comment}, fragment: {fragment}".format(
                        comment=test_data.get("comment"), fragment=fragment
                    ),
                )

        # self.assertTrue(False)

        self.assertEqual(
            self.activity.statuses.get("tags_found"),
            test_data.get("expected_tags_found_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("modify_xml"),
            test_data.get("expected_modify_xml_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("upload"),
            test_data.get("expected_upload_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        # assertion on activity log contents
        if test_data.get("expected_activity_log_contains"):
            for fragment in test_data.get("expected_activity_log_contains"):
                self.assertTrue(
                    fragment in str(self.activity.logger.loginfo),
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

        # assertion on cleaner.log contents
        if test_data.get("expected_cleaner_log_contains"):
            log_file_path = os.path.join(
                self.activity.get_tmp_dir(), self.activity.activity_log_file
            )
            with open(log_file_path, "r", encoding="utf8") as open_file:
                log_contents = open_file.read()
            for fragment in test_data.get("expected_cleaner_log_contains"):
                self.assertTrue(
                    fragment in log_contents,
                    "failed in {comment}".format(comment=test_data.get("comment")),
                )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_module, "find_disp_formula_tags")
    def test_do_activity_find_tags_exception(
        self,
        fake_find_disp_formula_tags,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        "test an exception raised when finding disp-formula tags in the XML"
        directory = TempDirectory()

        fake_session.return_value = self.session

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                self.session.get_value("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        exception_message = "An exception"
        fake_find_disp_formula_tags.side_effect = Exception(exception_message)

        expected_result = True

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "PreprintOcr, exception raised finding disp-formula and"
                " inline-formula tags for 10.7554/eLife.95901.2: %s"
            )
            % exception_message,
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(ocr, "ocr_files")
    def test_do_activity_ocr_exception(
        self,
        fake_ocr_files,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        "test an exception raised in OCR requests"
        directory = TempDirectory()

        fake_session.return_value = self.session

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                self.session.get_value("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]

        # write additional XML to the XML file
        add_body_article_xml(
            destination_path,
            (
                "<disp-formula>"
                '<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif"/>'
                "</disp-formula>"
            ),
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        exception_message = "An exception"
        fake_ocr_files.side_effect = Exception(exception_message)

        expected_result = True

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "PreprintOcr, exception raised in ocr_files for 10.7554/eLife.95901.2: %s"
            % exception_message,
        )

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(ocr, "ocr_files")
    @patch.object(activity_module, "rewrite_disp_formula_tags")
    def test_do_activity_xml_rewrite_exception(
        self,
        fake_rewrite_disp_formula_tags,
        fake_ocr_files,
        fake_cleaner_storage_context,
        fake_session,
        fake_storage_context,
    ):
        "test an exception raised rewriting XML"
        directory = TempDirectory()

        fake_session.return_value = self.session

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )

        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                self.session.get_value("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]

        # write additional XML to the XML file
        add_body_article_xml(
            destination_path,
            (
                "<disp-formula>"
                '<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif"/>'
                "</disp-formula>"
            ),
        )

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )

        fake_ocr_files.return_value = True

        exception_message = "An exception"
        fake_rewrite_disp_formula_tags.side_effect = Exception(exception_message)

        expected_result = True

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assert
        self.assertEqual(result, expected_result)
        self.assertEqual(
            self.activity.logger.logexception,
            "PreprintOcr, exception raised in rewriting XML for 10.7554/eLife.95901.2: %s"
            % exception_message,
        )


class TestMissingSetting(unittest.TestCase):
    "test do_activity() if required setting not defined"

    def setUp(self):
        fake_logger = FakeLogger()

        class FakeSettings:
            pass

        self.activity = activity_object(FakeSettings(), fake_logger, None, None, None)

    def test_do_activity_settings_no_endpoint(self):
        self.activity.settings = {}
        # do the activity
        result = self.activity.do_activity(input_data())

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "No mathpix_endpoint in settings, skipping PreprintOcr.",
        )


class TestBlankSetting(unittest.TestCase):
    "test do_activity() if required setting is empty"

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # change settings value
        self.mathpix_endpoint = self.activity.settings.mathpix_endpoint
        self.activity.settings.mathpix_endpoint = ""

    def tearDown(self):
        # restore settings value
        self.activity.settings.mathpix_endpoint = self.mathpix_endpoint

    def test_do_activity_settings_blank_endpoint(self):
        self.activity.settings.mathpix_endpoint = ""
        # do the activity
        result = self.activity.do_activity(input_data())

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "mathpix_endpoint in settings is blank, skipping PreprintOcr.",
        )


class TestFilePathsFromManifest(unittest.TestCase):
    "tests for file_paths_from_manifest()"

    def test_file_paths_from_manifest(self):
        "test matching file paths from manifest XML"
        xml_string = (
            '<manifest xmlns="http://manuscriptexchange.org" version="1.0">'
            '<item id="foo"/><item id="ueqn1" type="equation">'
            '<instance media-type="image/gif" href="content/681678v1_ueqn1.gif"/>'
            "</item>"
            '<item id="ueqn2" type="equation">'
            '<instance media-type="image/gif" href="content/681678v1_ueqn2.gif"/>'
            "</item>"
            '<item id="ueqn3" type="equation">'
            '<instance media-type="image/gif" href="content/681678v1_ueqn3.gif"/>'
            "</item>"
            '<item id="inline1" type="equation">'
            '<instance media-type="image/gif" href="content/5681678v1_inline1.gif"/>'
            "</item></manifest>"
        )
        manifest_root = ElementTree.fromstring(xml_string)
        graphic_image_names = ["681678v1_ueqn1.gif"]
        inline_graphic_image_names = ["5681678v1_inline1.gif"]
        version_doi = "10.7554/eLife.95901.2"
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        (
            graphic_file_to_path_map,
            inline_graphic_file_to_path_map,
        ) = activity_module.file_paths_from_manifest(
            manifest_root,
            graphic_image_names,
            inline_graphic_image_names,
            version_doi,
            caller_name,
            logger,
        )
        # assert
        self.assertDictEqual(
            graphic_file_to_path_map,
            {"681678v1_ueqn1.gif": "content/681678v1_ueqn1.gif"},
        )
        self.assertDictEqual(
            inline_graphic_file_to_path_map,
            {"5681678v1_inline1.gif": "content/5681678v1_inline1.gif"},
        )


class TestDownloadGraphics(unittest.TestCase):
    "tests for download_graphics()"

    def setUp(self):
        self.fake_logger = FakeLogger()
        self.resource_prefix = "s3://bot_bucket/expanded_files"
        self.file_name_map = {
            "681678v1_ueqn1.gif": "content/681678v1_ueqn1.gif",
            "681678v1_ueqn3.gif": "content/681678v1_ueqn3.gif",
        }
        self.directory = TempDirectory()
        resources = [
            "expanded_files/content/681678v1_ueqn1.gif",
            "expanded_files/content/681678v1_ueqn2.gif",
            "expanded_files/content/681678v1_ueqn3.gif",
        ]
        self.storage = FakeStorageContext(self.directory.path, resources)
        # populate the bucket contents
        for resource in resources:
            file_path = os.path.join(self.directory.path, resource)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            shutil.copyfile(
                "tests/files_source/digests/outbox/99999/digest-99999.jpg",
                file_path,
            )

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_download_graphics(self):
        "test downloading files from bucket"
        to_dir = os.path.join(self.directory.path, "tmp")
        caller_name = "test"
        # invoke
        activity_module.download_graphics(
            self.storage,
            self.resource_prefix,
            self.file_name_map,
            to_dir,
            caller_name,
            self.fake_logger,
        )
        # assert
        self.assertTrue(
            (
                "%s, downloading s3://bot_bucket/expanded_files/content/681678v1_ueqn1.gif"
                " to %s/content/681678v1_ueqn1.gif"
            )
            % (caller_name, to_dir)
            in self.fake_logger.loginfo
        )
        self.assertEqual(
            sorted(os.listdir(os.path.join(to_dir, "content"))),
            sorted(["681678v1_ueqn1.gif", "681678v1_ueqn3.gif"]),
        )

    @patch.object(FakeStorageContext, "get_resource_to_file")
    def test_exception(self, fake_get_resource_to_file):
        "test exception raised downloading a file"
        to_dir = os.path.join(self.directory.path, "tmp")
        caller_name = "test"
        exception_message = "An exception"
        fake_get_resource_to_file.side_effect = Exception(exception_message)
        # invoke
        activity_module.download_graphics(
            self.storage,
            self.resource_prefix,
            self.file_name_map,
            to_dir,
            caller_name,
            self.fake_logger,
        )
        # assert
        self.assertEqual(
            self.fake_logger.logexception,
            "%s, exception downloading storage_resource_origin 681678v1_ueqn3.gif: %s"
            % (caller_name, exception_message),
        )


class TestFindOcrTags(unittest.TestCase):
    "tests for find_ocr_tags()"

    def test_find_ocr_tags(self):
        "test finding disp-formula tags from full XML"
        tag_name = "disp-formula"
        xml_string = (
            '<article xmlns:mml="http://www.w3.org/1998/Math/MathML" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<disp-formula id="ueqn1">\n'
            '<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif"/>\n'
            "</disp-formula>\n"
            '<disp-formula id="ueqn2">\n'
            "<alternatives>\n"
            "<mml:math>...</mml:math>\n"
            '<graphic xlink:href="681678v1_ueqn2.gif" mimetype="image" mime-subtype="gif"/>\n'
            "</alternatives>\n"
            "</disp-formula>\n"
            '<disp-formula id="ueqn3">\n'
            '<graphic xlink:href="681678v1_ueqn3.gif" mimetype="image" mime-subtype="gif"/>\n'
            "</disp-formula>\n"
            "<inline-formula>\n"
            '<inline-graphic xlink:href="5681678v1_inline1.gif"'
            ' mimetype="image" mime-subtype="gif"/>\n'
            "</inline-formula>\n"
            "</article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        # invoke
        result = activity_module.find_ocr_tags(xml_root, tag_name)
        # assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].tag, tag_name)


class TestFindDispFormulaTags(unittest.TestCase):
    "tests for find_disp_formula_tags()"

    def test_find_disp_formula_tags(self):
        "test finding disp-formula tags to OCR"
        xml_string = (
            '<article xmlns:mml="http://www.w3.org/1998/Math/MathML" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<disp-formula id="ueqn1">\n'
            '<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif"/>\n'
            "</disp-formula>\n"
            '<disp-formula id="ueqn2">\n'
            "<alternatives>\n"
            "<mml:math>...</mml:math>\n"
            '<graphic xlink:href="681678v1_ueqn2.gif" mimetype="image" mime-subtype="gif"/>\n'
            "</alternatives>\n"
            "</disp-formula>\n"
            "</article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        # invoke
        result = activity_module.find_disp_formula_tags(xml_root)
        # assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tag, "disp-formula")


class TestFindInlineFormulaTags(unittest.TestCase):
    "tests for find_inline_formula_tags()"

    def test_find_inline_formula_tags(self):
        "test finding inline-formula tags to OCR"
        xml_string = (
            '<article xmlns:mml="http://www.w3.org/1998/Math/MathML" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<inline-formula>\n"
            '<inline-graphic xlink:href="5681678v1_inline1.gif"'
            ' mimetype="image" mime-subtype="gif"/>\n'
            "</inline-formula>\n"
            "<inline-formula>\n"
            '<inline-graphic xlink:href="5681678v1_inline2.gif"'
            ' mimetype="image" mime-subtype="gif"/>\n'
            "<alternatives>\n"
            "<mml:math/>\n"
            "</alternatives>\n"
            "</inline-formula>\n"
            "</article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        # invoke
        result = activity_module.find_inline_formula_tags(xml_root)
        # assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tag, "inline-formula")


class TestRewriteDispFormulaTags(unittest.TestCase):
    "tests for rewrite_disp_formula_tags()"

    def setUp(self):
        self.disp_formula_tag_1_xml_string = (
            b'<disp-formula xmlns:xlink="http://www.w3.org/1999/xlink" id="ueqn1">\n'
            b'<graphic xlink:href="681678v1_ueqn1.gif" mimetype="image" mime-subtype="gif" />\n'
            b"</disp-formula>\n"
        )
        disp_formula_tag_1 = ElementTree.fromstring(self.disp_formula_tag_1_xml_string)

        self.disp_formula_tags = [disp_formula_tag_1]
        self.file_to_data_map = {
            "681678v1_ueqn1.gif": {
                "data": test_activity_data.EXAMPLE_OCR_RESPONSE_JSON.get("data")
            }
        }

        # can assert expected XML in multiple test scenarios
        self.expected_disp_formula_tag_1_xml_string = (
            b'<disp-formula xmlns:mml="http://www.w3.org/1998/Math/MathML"'
            b' xmlns:xlink="http://www.w3.org/1999/xlink" id="ueqn1">\n'
            b"<alternatives>"
            b'<mml:math alttext="\\tau \\frac{d \\boldsymbol{a}}{d t}='
            b'\\boldsymbol{C a}+\\boldsymbol{b}">\n'
            b"  <mml:mi>&#964;</mml:mi>\n"
            b"  <mml:mfrac>\n"
            b"    <mml:mrow>\n"
            b"      <mml:mi>d</mml:mi>\n"
            b'      <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
            b"    </mml:mrow>\n"
            b"    <mml:mrow>\n"
            b"      <mml:mi>d</mml:mi>\n"
            b"      <mml:mi>t</mml:mi>\n"
            b"    </mml:mrow>\n"
            b"  </mml:mfrac>\n"
            b"  <mml:mo>=</mml:mo>\n"
            b'  <mml:mi mathvariant="bold-italic">C</mml:mi>\n'
            b'  <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
            b"  <mml:mo>+</mml:mo>\n"
            b'  <mml:mi mathvariant="bold-italic">b</mml:mi>\n'
            b"</mml:math>"
            b'<graphic xlink:href="681678v1_ueqn1.gif"'
            b' mimetype="image" mime-subtype="gif" />\n'
            b"</alternatives>"
            b"</disp-formula>"
        )

    def test_rewrite_disp_formula_tags(self):
        "test adding math XML to disp-formula tags"
        fake_logger = FakeLogger()
        # invoke
        activity_module.rewrite_disp_formula_tags(
            self.disp_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertEqual(
            ElementTree.tostring(self.disp_formula_tags[0]),
            self.expected_disp_formula_tag_1_xml_string,
        )

    def test_existing_alternatives_tag(self):
        "test if there is already an alternatives tag in the XML"
        fake_logger = FakeLogger()
        xml_string = self.disp_formula_tag_1_xml_string.replace(
            b"</disp-formula>", b"<alternatives /></disp-formula>"
        )
        disp_formula_tags = [ElementTree.fromstring(xml_string)]
        # invoke
        activity_module.rewrite_disp_formula_tags(
            disp_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertEqual(
            ElementTree.tostring(disp_formula_tags[0]),
            self.expected_disp_formula_tag_1_xml_string,
        )

    def test_no_graphic_tag(self):
        "test if no graphic tag inside the XML"
        fake_logger = FakeLogger()
        xml_string = b"<disp-formula />"
        disp_formula_tags = [ElementTree.fromstring(xml_string)]
        # invoke
        activity_module.rewrite_disp_formula_tags(
            disp_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertEqual(
            ElementTree.tostring(disp_formula_tags[0]),
            xml_string,
        )
        self.assertEqual(
            fake_logger.loginfo[-1],
            "no graphic tag found in b'%s'" % xml_string.decode("utf-8"),
        )

    @patch.object(ElementTree, "fromstring")
    def test_parse_exception(self, fake_fromstring):
        "test if parsing math XML raises an exception"
        fake_logger = FakeLogger()
        fake_fromstring.side_effect = ParseError("An exception")
        # invoke
        activity_module.rewrite_disp_formula_tags(
            self.disp_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertTrue(
            ElementTree.tostring(self.disp_formula_tags[0])
            in self.disp_formula_tag_1_xml_string,
        )
        self.assertTrue(
            "rewrite disp-formula tags XML ParseError exception parsing XML <math "
            in fake_logger.logexception
        )


class TestRewriteInlineFormulaTags(unittest.TestCase):
    "tests for rewrite_inline_formula_tags()"

    def setUp(self):
        self.inline_formula_tag_1_xml_string = (
            b'<inline-formula xmlns:xlink="http://www.w3.org/1999/xlink">\n'
            b'<inline-graphic xlink:href="5681678v1_inline1.gif"'
            b' mimetype="image" mime-subtype="gif" />\n'
            b"</inline-formula>\n"
        )
        inline_formula_tag_1 = ElementTree.fromstring(
            self.inline_formula_tag_1_xml_string
        )

        self.inline_formula_tags = [inline_formula_tag_1]
        self.file_to_data_map = {
            "5681678v1_inline1.gif": {
                "data": test_activity_data.EXAMPLE_OCR_RESPONSE_JSON.get("data")
            }
        }

    def test_rewrite_inline_formula_tags(self):
        "test adding math XML to inline-formula tags"
        fake_logger = FakeLogger()
        expected_inline_formula_tag_1_xml_string = (
            b'<inline-formula xmlns:mml="http://www.w3.org/1998/Math/MathML"'
            b' xmlns:xlink="http://www.w3.org/1999/xlink">\n'
            b"<alternatives>"
            b'<mml:math alttext="\\tau \\frac{d \\boldsymbol{a}}{d t}='
            b'\\boldsymbol{C a}+\\boldsymbol{b}">\n'
            b"  <mml:mi>&#964;</mml:mi>\n"
            b"  <mml:mfrac>\n"
            b"    <mml:mrow>\n"
            b"      <mml:mi>d</mml:mi>\n"
            b'      <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
            b"    </mml:mrow>\n"
            b"    <mml:mrow>\n"
            b"      <mml:mi>d</mml:mi>\n"
            b"      <mml:mi>t</mml:mi>\n"
            b"    </mml:mrow>\n"
            b"  </mml:mfrac>\n"
            b"  <mml:mo>=</mml:mo>\n"
            b'  <mml:mi mathvariant="bold-italic">C</mml:mi>\n'
            b'  <mml:mi mathvariant="bold-italic">a</mml:mi>\n'
            b"  <mml:mo>+</mml:mo>\n"
            b'  <mml:mi mathvariant="bold-italic">b</mml:mi>\n'
            b"</mml:math>"
            b'<inline-graphic xlink:href="5681678v1_inline1.gif"'
            b' mimetype="image" mime-subtype="gif" />\n'
            b"</alternatives>"
            b"</inline-formula>"
        )
        # invoke
        activity_module.rewrite_inline_formula_tags(
            self.inline_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertEqual(
            ElementTree.tostring(self.inline_formula_tags[0]),
            expected_inline_formula_tag_1_xml_string,
        )

    @patch.object(ElementTree, "fromstring")
    def test_parse_exception(self, fake_fromstring):
        "test if parsing math XML raises an exception"
        fake_logger = FakeLogger()
        fake_fromstring.side_effect = ParseError("An exception")
        # invoke
        activity_module.rewrite_inline_formula_tags(
            self.inline_formula_tags, self.file_to_data_map, fake_logger
        )
        # assert
        self.assertTrue(
            ElementTree.tostring(self.inline_formula_tags[0])
            in self.inline_formula_tag_1_xml_string,
        )
        self.assertTrue(
            "rewrite inline-formula tags XML ParseError exception parsing XML <math "
            in fake_logger.logexception
        )
