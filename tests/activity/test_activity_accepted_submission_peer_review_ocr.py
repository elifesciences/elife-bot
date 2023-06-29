# coding=utf-8

import copy
import os
import glob
import shutil
import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data
from provider import cleaner
import activity.activity_AcceptedSubmissionPeerReviewOcr as activity_module
from activity.activity_AcceptedSubmissionPeerReviewOcr import (
    activity_AcceptedSubmissionPeerReviewOcr as activity_object,
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


EXAMPLE_RESPONSE_JSON = {
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
    "text": "$\\tau \\frac{d \\boldsymbol{a}}{d t}=\\boldsymbol{C a}+\\boldsymbol{b}$",
    "data": [
        {
            "type": "mathml",
            "value": '<math xmlns="http://www.w3.org/1998/Math/MathML">\n  <mi>τ</mi>\n  <mfrac>\n    <mrow>\n      <mi>d</mi>\n      <mi mathvariant="bold-italic">a</mi>\n    </mrow>\n    <mrow>\n      <mi>d</mi>\n      <mi>t</mi>\n    </mrow>\n  </mfrac>\n  <mo>=</mo>\n  <mi mathvariant="bold-italic">C</mi>\n  <mi mathvariant="bold-italic">a</mi>\n  <mo>+</mo>\n  <mi mathvariant="bold-italic">b</mi>\n</math>',
        },
        {
            "type": "latex",
            "value": "\\tau \\frac{d \\boldsymbol{a}}{d t}=\\boldsymbol{C a}+\\boldsymbol{b}",
        },
    ],
}


EQUATION_DATA = EXAMPLE_RESPONSE_JSON.get("data")


OCR_FILES_DATA = {
    "sa1-inf1.jpg": {
        "data": EQUATION_DATA,
    },
    "sa1-inf2.jpg": {
        "data": EQUATION_DATA,
    },
    "sa2-inf1.jpg": {
        "data": [],
    },
}


@ddt
class TestAcceptedSubmissionPeerReviewOcr(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(
            copy.copy(test_activity_data.accepted_session_example)
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("cleaner_log", None)

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    @patch.object(activity_module, "ocr_files")
    @patch.object(cleaner, "storage_context")
    @patch.object(activity_object, "clean_tmp_dir")
    @data(
        {
            "comment": "example with no inline-graphic",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "image_names": None,
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": None,
            "expected_upload_xml_status": None,
            "expected_activity_log_contains": [
                (
                    "AcceptedSubmissionPeerReviewOcr, no inline-graphic tags in "
                    "30-01-2019-RA-eLife-45644.zip"
                )
            ],
        },
        {
            "comment": "example with three types of inline-graphic math formula or not",
            "filename": "30-01-2019-RA-eLife-45644.zip",
            "sub_article_xml": (
                '<sub-article id="sa1">'
                "<body>"
                '<p>First paragraph with an inline equation <inline-graphic xlink:href="sa1-inf1.jpg"/>.</p>'
                "<p>Following is a display formula:</p>"
                '<p><inline-graphic xlink:href="sa1-inf2.jpg"/></p>'
                "</body>"
                "</sub-article>"
                '<sub-article id="sa2">'
                "<body>"
                '<p>Next can be an image containing no formula <inline-graphic xlink:href="sa2-inf1.jpg"/>.</p>'
                "</body>"
                "</sub-article>"
            ),
            "image_names": ["sa1-inf1.jpg", "sa1-inf2.jpg", "sa2-inf1.jpg"],
            "expected_result": True,
            "expected_docmap_string_status": True,
            "expected_hrefs_status": True,
            "expected_upload_xml_status": True,
            "expected_xml_contains": [
                (
                    '<sub-article id="sa1">'
                    "<body>"
                    "<p>First paragraph with an inline equation <inline-formula>"
                    '<mml:math alttext="'
                    r"\tau \frac{d \boldsymbol{a}}{d t}=\boldsymbol{C a}+\boldsymbol{b}"
                    '">\n'
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
                    "</mml:math>"
                    "</inline-formula>.</p>"
                    "<p>Following is a display formula:</p>"
                    "<p><disp-formula>"
                    '<mml:math alttext="'
                    r"\tau \frac{d \boldsymbol{a}}{d t}=\boldsymbol{C a}+\boldsymbol{b}"
                    '">\n'
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
                    "</mml:math>"
                    "</disp-formula></p>"
                    "</body>"
                    "</sub-article>"
                    '<sub-article id="sa2">'
                    "<body>"
                    '<p>Next can be an image containing no formula <inline-graphic xlink:href="sa2-inf1.jpg"/>.</p>'
                    "</body>"
                    "</sub-article>"
                ),
                (
                    '<file file-type="figure">'
                    "<upload_file_nm>sa2-inf1.jpg</upload_file_nm>"
                    "</file>"
                    "</files>"
                ),
            ],
            "expected_xml_not_contains": [
                "<upload_file_nm>sa1-inf1.jpg</upload_file_nm>",
                "<upload_file_nm>sa1-inf2.jpg</upload_file_nm>",
            ],
            "expected_bucket_upload_folder_contents": [
                "30-01-2019-RA-eLife-45644.xml",
                "sa2-inf1.jpg",
            ],
            "expected_bucket_upload_folder_not_contents": [
                "sa1-inf1.jpg",
                "sa1-inf2.jpg",
            ],
        },
    )
    def test_do_activity(
        self,
        test_data,
        fake_clean_tmp_dir,
        fake_cleaner_storage_context,
        fake_ocr_files,
        fake_session,
        fake_storage_context,
    ):
        # set REPAIR_XML value because test fixture is malformed XML
        activity_module.REPAIR_XML = True
        directory = TempDirectory()
        fake_clean_tmp_dir.return_value = None

        zip_sub_folder = test_data.get("filename").replace(".zip", "")
        zip_xml_file = "%s.xml" % zip_sub_folder

        # create a new zip file fixtur
        file_details = []
        if test_data.get("image_names"):
            for image_name in test_data.get("image_names"):
                details = {
                    "file_path": "tests/files_source/digests/outbox/99999/digest-99999.jpg",
                    "file_type": "figure",
                    "upload_file_nm": image_name,
                }
                file_details.append(details)
        new_zip_file_path = helpers.add_files_to_accepted_zip(
            "tests/files_source/30-01-2019-RA-eLife-45644.zip",
            directory.path,
            file_details,
        )

        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            new_zip_file_path,
        )

        # write additional XML to the XML file
        if test_data.get("sub_article_xml"):
            sub_folder = test_data.get("filename").rsplit(".", 1)[0]
            xml_path = os.path.join(
                directory.path,
                self.session.get_value("expanded_folder"),
                sub_folder,
                "%s.xml" % sub_folder,
            )
            with open(xml_path, "r", encoding="utf-8") as open_file:
                xml_string = open_file.read()
            with open(xml_path, "w", encoding="utf-8") as open_file:
                xml_string = xml_string.replace(
                    "</article>", "%s</article>" % test_data.get("sub_article_xml")
                )
                open_file.write(xml_string)

        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_session.return_value = self.session
        fake_ocr_files.return_value = OCR_FILES_DATA

        # do the activity
        result = self.activity.do_activity(input_data(test_data.get("filename")))
        self.assertEqual(result, test_data.get("expected_result"))

        temp_dir_files = glob.glob(self.activity.directories.get("TEMP_DIR") + "/*/*")
        xml_file_path = os.path.join(
            self.activity.directories.get("TEMP_DIR"),
            zip_sub_folder,
            zip_xml_file,
        )
        self.assertTrue(xml_file_path in temp_dir_files)

        # assertion on XML contents
        if test_data.get("expected_xml_contains") or test_data.get(
            "expected_xml_not_contains"
        ):
            with open(xml_file_path, "r", encoding="utf-8") as open_file:
                xml_content = open_file.read()
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

        self.assertEqual(
            self.activity.statuses.get("hrefs"),
            test_data.get("expected_hrefs_status"),
            "failed in {comment}".format(comment=test_data.get("comment")),
        )

        self.assertEqual(
            self.activity.statuses.get("upload_xml"),
            test_data.get("expected_upload_xml_status"),
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

        # assertion on the session cleaner log content
        if test_data.get("expected_upload_xml_status"):
            session_log = self.session.get_value("cleaner_log")
            self.assertIsNotNone(
                session_log,
                "failed in {comment}".format(comment=test_data.get("comment")),
            )

        # check output bucket folder contents
        if (
            "expected_bucket_upload_folder_contents" in test_data
            or "expected_bucket_upload_folder_not_contents" in test_data
        ):
            bucket_folder_path = os.path.join(
                directory.path,
                test_activity_data.accepted_session_example.get("expanded_folder"),
                zip_sub_folder,
            )
            try:
                output_bucket_list = os.listdir(bucket_folder_path)
            except FileNotFoundError:
                # no objects were uploaded so the folder path does not exist
                output_bucket_list = []
            for bucket_file in test_data.get(
                "expected_bucket_upload_folder_contents", []
            ):
                self.assertTrue(
                    bucket_file in output_bucket_list,
                    "%s not found in bucket upload folder" % bucket_file,
                )
            for bucket_file in test_data.get(
                "expected_bucket_upload_folder_not_contents", []
            ):
                self.assertTrue(
                    bucket_file not in output_bucket_list,
                    "%s unexpectedly found in bucket upload folder" % bucket_file,
                )

        # reset REPAIR_XML value
        activity_module.REPAIR_XML = False

    @patch.object(activity_module, "get_session")
    @patch.object(cleaner, "storage_context")
    @patch.object(cleaner, "file_list")
    def test_do_activity_exception_parseerror(
        self,
        fake_file_list,
        fake_cleaner_storage_context,
        fake_session,
    ):
        "test if there is an XML ParseError when getting a file list"
        directory = TempDirectory()
        zip_file_base = "28-09-2020-RA-eLife-63532"
        zip_file = "%s.zip" % zip_file_base
        session_dict = copy.copy(test_activity_data.accepted_session_example)
        session_dict["input_filename"] = zip_file
        fake_session.return_value = FakeSession(session_dict)
        zip_file_path = os.path.join(
            test_activity_data.ExpandArticle_files_source_folder,
            zip_file,
        )
        resources = helpers.expanded_folder_bucket_resources(
            directory,
            test_activity_data.accepted_session_example.get("expanded_folder"),
            zip_file_path,
        )

        # write additional XML to the XML file
        sub_article_xml = (
            "<sub-article>"
            "<body>"
            '<p><inline-graphic xlink:href="sa1-inf1.jpg"/>.</p>'
            "</body>"
            "</sub-article>"
        )
        xml_path = os.path.join(
            directory.path,
            session_dict.get("expanded_folder"),
            zip_file_base,
            "%s.xml" % zip_file_base,
        )
        with open(xml_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
        with open(xml_path, "w", encoding="utf-8") as open_file:
            xml_string = xml_string.replace(
                "</article>", "%s</article>" % sub_article_xml
            )
            open_file.write(xml_string)

        fake_cleaner_storage_context.return_value = FakeStorageContext(
            directory.path, resources
        )
        fake_file_list.side_effect = ParseError()
        # do the activity
        result = self.activity.do_activity(input_data(zip_file))
        self.assertEqual(result, True)
        expected_logexception = (
            "AcceptedSubmissionPeerReviewOcr, XML ParseError exception "
            "in cleaner.file_list parsing XML file %s.xml for file %s"
        ) % (zip_file_base, zip_file)
        self.assertEqual(self.activity.logger.logexception, expected_logexception)

    def test_do_activity_settings_no_endpoint(self):
        self.activity.settings = {}
        # do the activity
        result = self.activity.do_activity(input_data())

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "No mathpix_endpoint in settings, skipping AcceptedSubmissionPeerReviewOcr.",
        )

    def test_do_activity_settings_blank_endpoint(self):
        self.activity.settings.mathpix_endpoint = ""
        # do the activity
        result = self.activity.do_activity(input_data())

        # check assertions
        self.assertEqual(result, self.activity.ACTIVITY_SUCCESS)
        self.assertEqual(
            self.activity.logger.loginfo[-1],
            "mathpix_endpoint in settings is blank, skipping AcceptedSubmissionPeerReviewOcr.",
        )


class TestOcrFiles(unittest.TestCase):
    "test ocr_files()"

    def setUp(self):
        self.logger = FakeLogger()
        self.file_name = "sa1-inf1.jpg"
        self.file_path = "tests/files_source/digests/outbox/99999/digest-99999.jpg"
        self.file_to_path_map = {self.file_name: self.file_path}
        self.identifier = "test.zip"

    @patch("requests.post")
    def test_ocr_files(self, fake_request):
        "test a request to the ocr endpoint but mocking the requests.post"
        response_json = {}
        response_status = 200
        response = FakeResponse(response_status)
        response.response_json = response_json
        fake_request.return_value = response
        expected_result = {self.file_name: response_json}
        # invoke
        result = activity_module.ocr_files(
            self.file_to_path_map, settings_mock, self.logger, self.identifier
        )
        # assert
        self.assertDictEqual(result, expected_result)

    @patch("requests.post")
    def test_failure_status_code(self, fake_request):
        "test exception catching of a non-success status code response"
        response_json = {}
        response_status = 500
        response = FakeResponse(response_status)
        response.response_json = response_json
        fake_request.return_value = response
        expected_result = {}
        excepted_log_message = (
            "Exception posting to Mathpix API endpoint, file_name %s: "
            "Error in mathpix_post_request %s to Mathpix API: %s\nNone"
            % (self.file_name, self.file_path, response_status)
        )
        # invoke
        result = activity_module.ocr_files(
            self.file_to_path_map, settings_mock, self.logger, self.identifier
        )
        # assert
        self.assertDictEqual(result, expected_result)
        # test for logging
        self.assertEqual(self.logger.logexception, excepted_log_message)


class TestMathDataParts(unittest.TestCase):
    "test math_data_parts()"

    def test_math_data_parts(self):
        "test expected input"
        math_data = EQUATION_DATA
        mathml_data, latex_data = activity_module.math_data_parts(math_data)
        self.assertTrue(isinstance(mathml_data, dict))
        self.assertTrue(isinstance(latex_data, dict))
        self.assertEqual(list(mathml_data.keys()), ["type", "value"])
        self.assertEqual(list(latex_data.keys()), ["type", "value"])

    def test_empty_list(self):
        "test when data is an empty list"
        math_data = []
        mathml_data, latex_data = activity_module.math_data_parts(math_data)
        self.assertEqual(mathml_data, None)
        self.assertEqual(latex_data, None)


class TestTransformInlineGraphicTags(unittest.TestCase):
    "test transform_inline_graphic_tags()"

    def setUp(self):
        self.logger = FakeLogger()
        self.identifier = "test.zip"

    def test_inline_formula(self):
        "test transforming one inline-graphic tag into inline-formula"
        xml_string = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<p>Test inline formula <inline-graphic xlink:href="sa1-inf1.jpg"/>.</p>'
            "</sub-article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        file_to_math_data_map = {
            "sa1-inf1.jpg": {
                "data": [
                    {
                        "type": "mathml",
                        "value": (
                            '<math xmlns="http://www.w3.org/1998/Math/MathML">'
                            "<mi>τ</mi>"
                            "</math>"
                        ),
                    }
                ]
            }
        }
        expected = (
            b'<sub-article xmlns:mml="http://www.w3.org/1998/Math/MathML">'
            b"<p>Test inline formula "
            b"<inline-formula><mml:math><mml:mi>&#964;</mml:mi></mml:math></inline-formula>"
            b".</p>"
            b"</sub-article>"
        )
        activity_module.transform_inline_graphic_tags(
            xml_root, file_to_math_data_map, self.logger, self.identifier
        )
        self.assertEqual(ElementTree.tostring(xml_root), expected)

    def test_disp_formula(self):
        "test transforming one inline-graphic tag into disp-formula"
        xml_string = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<p><inline-graphic xlink:href="sa1-inf1.jpg"/></p>'
            "</sub-article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        file_to_math_data_map = {
            "sa1-inf1.jpg": {
                "data": [
                    {
                        "type": "mathml",
                        "value": (
                            '<math xmlns="http://www.w3.org/1998/Math/MathML">'
                            "<mi>τ</mi></math>"
                        ),
                    }
                ]
            }
        }
        expected = (
            b'<sub-article xmlns:mml="http://www.w3.org/1998/Math/MathML">'
            b"<p><disp-formula><mml:math><mml:mi>&#964;</mml:mi></mml:math></disp-formula>"
            b"</p></sub-article>"
        )
        activity_module.transform_inline_graphic_tags(
            xml_root, file_to_math_data_map, self.logger, self.identifier
        )
        self.assertEqual(ElementTree.tostring(xml_root), expected)

    def test_multiple_inline_formula(self):
        "test transforming one inline-graphic tag into disp-formula"
        xml_string = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<p>First formula <inline-graphic xlink:href="sa1-inf1.jpg"/>, '
            'second formula <inline-graphic xlink:href="sa1-inf1.jpg"/>.</p>'
            "</sub-article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        file_to_math_data_map = {
            "sa1-inf1.jpg": {
                "data": [
                    {
                        "type": "mathml",
                        "value": (
                            '<math xmlns="http://www.w3.org/1998/Math/MathML">'
                            "<mi>τ</mi></math>"
                        ),
                    }
                ]
            }
        }
        expected = (
            b'<sub-article xmlns:mml="http://www.w3.org/1998/Math/MathML">'
            b"<p>First formula "
            b"<inline-formula><mml:math><mml:mi>&#964;</mml:mi></mml:math></inline-formula>, "
            b"second formula "
            b"<inline-formula><mml:math><mml:mi>&#964;</mml:mi></mml:math></inline-formula>."
            b"</p></sub-article>"
        )
        activity_module.transform_inline_graphic_tags(
            xml_root, file_to_math_data_map, self.logger, self.identifier
        )
        self.assertEqual(ElementTree.tostring(xml_root), expected)

    def test_xml_exception(self):
        "test exception raised when parsing mathml"
        xml_string = (
            '<sub-article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<p><inline-graphic xlink:href="sa1-inf1.jpg" /></p>'
            "</sub-article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        file_to_math_data_map = {
            "sa1-inf1.jpg": {
                "data": [
                    {
                        "type": "mathml",
                        "value": ("<malformed>"),
                    }
                ]
            }
        }
        expected = bytes(xml_string, encoding="utf-8")
        activity_module.transform_inline_graphic_tags(
            xml_root, file_to_math_data_map, self.logger, self.identifier
        )
        self.assertEqual(ElementTree.tostring(xml_root), expected)

    def test_empty_inputs(self):
        "test minimal XML and minimal inputs"
        xml_string = "<sub-article/>"
        xml_root = ElementTree.fromstring(xml_string)
        file_to_math_data_map = {}
        expected = b"<sub-article />"
        activity_module.transform_inline_graphic_tags(
            xml_root, file_to_math_data_map, self.logger, self.identifier
        )
        self.assertEqual(ElementTree.tostring(xml_root), expected)
