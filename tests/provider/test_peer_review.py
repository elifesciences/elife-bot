# coding=utf-8

import os
import unittest
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
from elifecleaner.transform import ArticleZipFile
from tests.activity.classes_mock import FakeLogger, FakeResponse
from provider import peer_review


class TestDownloadFile(unittest.TestCase):
    "tests for download_file()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.get")
    def test_download_file(self, fake_get):
        "test downloading file by GET request to disk"
        fake_get.return_value = FakeResponse(200, content=b"test")
        directory = TempDirectory()
        from_path = "https://example.org/from.jpg"
        to_file = os.path.join(directory.path, "to.jpg")
        user_agent = "test"
        # invoke
        result = peer_review.download_file(from_path, to_file, user_agent)
        # assert
        self.assertEqual(result, to_file)

    @patch("requests.get")
    def test_exception(self, fake_get):
        "test requests raises exception"
        fake_get.return_value = FakeResponse(404)
        directory = TempDirectory()
        from_path = "https://example.org/from.jpg"
        to_file = os.path.join(directory.path, "to.jpg")
        user_agent = "test"
        # invoke
        with self.assertRaises(RuntimeError):
            peer_review.download_file(from_path, to_file, user_agent)


class TestDownloadImages(unittest.TestCase):
    "tests for download_images()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.get")
    def test_download_images(self, fake_get):
        "test download a list of images"
        fake_get.return_value = FakeResponse(200, content=b"test")
        logger = FakeLogger()
        directory = TempDirectory()
        from_url = "https://example.org/from.jpg"
        href_list = [from_url, from_url]
        to_dir = directory.path
        activity_name = "MecaPeerReviewImages"
        user_agent = "test"
        expected = {href_list[0]: os.path.join(directory.path, "from.jpg")}
        # invoke
        result = peer_review.download_images(
            href_list, to_dir, activity_name, logger, user_agent
        )
        # assert
        self.assertDictEqual(result, expected)
        self.assertEqual(
            logger.loginfo[-1],
            "%s, href %s was already downloaded" % (activity_name, from_url),
        )
        self.assertEqual(
            logger.loginfo[-2],
            "%s, downloaded href %s to %s/from.jpg"
            % (activity_name, from_url, directory.path),
        )

    @patch("requests.get")
    def test_exception(self, fake_get):
        "test exception raised downloading images"
        fake_get.return_value = FakeResponse(404)
        logger = FakeLogger()
        directory = TempDirectory()
        from_url = "https://example.org/from.jpg"
        href_list = [from_url]
        to_dir = directory.path
        activity_name = "MecaPeerReviewImages"
        user_agent = "test"
        expected = {}
        # invoke
        result = peer_review.download_images(
            href_list, to_dir, activity_name, logger, user_agent
        )
        # assert
        self.assertDictEqual(result, expected)
        self.assertEqual(
            logger.loginfo[-1],
            "%s, href %s could not be downloaded" % (activity_name, from_url),
        )
        self.assertEqual(
            logger.loginfo[-2],
            "GET request returned a 404 status code for %s" % from_url,
        )


class TestGenerateNewImageFileNames(unittest.TestCase):
    "tests for generate_new_image_file_names()"

    def test_generate_new_image_file_names(self):
        "test generating new file name and details for image files"
        href_to_file_name_map = {
            "https://i.imgur.com/vc4GR10.png": "tmp/2024-11-04.23.52.26/input_dir/vc4GR10.png",
            "https://i.imgur.com/FFeuydR.jpg": "tmp/2024-11-04.23.52.26/input_dir/FFeuydR.jpg",
        }
        article_id = "95901"
        identifier = "10.7554/eLife.95901.1"
        caller_name = "MecaPeerReviewImages"
        logger = FakeLogger()
        expected = [
            {
                "from_href": "https://i.imgur.com/vc4GR10.png",
                "file_name": "tmp/2024-11-04.23.52.26/input_dir/vc4GR10.png",
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf1.png",
                "id": "inf1",
            },
            {
                "from_href": "https://i.imgur.com/FFeuydR.jpg",
                "file_name": "tmp/2024-11-04.23.52.26/input_dir/FFeuydR.jpg",
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf2.jpg",
                "id": "inf2",
            },
        ]
        # invoke
        result = peer_review.generate_new_image_file_names(
            href_to_file_name_map,
            article_id,
            identifier,
            caller_name,
            logger,
        )
        # assert
        self.assertEqual(len(result), 2)
        for index, file_details in enumerate(result):
            self.assertDictEqual(file_details, expected[index])
        self.assertEqual(
            logger.loginfo[-1],
            (
                "%s, for %s, file name tmp/2024-11-04.23.52.26/input_dir/FFeuydR.jpg"
                " changed to file name elife-95901-inf2.jpg" % (caller_name, identifier)
            ),
        )
        self.assertEqual(
            logger.loginfo[-2],
            (
                "%s, for %s, file name tmp/2024-11-04.23.52.26/input_dir/vc4GR10.png"
                " changed to file name elife-95901-inf1.png" % (caller_name, identifier)
            ),
        )


class TestGenerateNewImageFilePaths(unittest.TestCase):
    "tests for generate_new_image_file_paths()"

    def test_generate_new_image_file_paths(self):
        "test generating new image file path values"
        file_details_list = [
            {
                "upload_file_nm": "elife-95901-inf1.png",
            },
            {
                "upload_file_nm": "elife-95901-inf2.jpg",
            },
        ]
        content_subfolder = "content"
        identifier = "10.7554/eLife.95901.1"
        caller_name = "MecaPeerReviewImages"
        logger = FakeLogger()
        expected = [
            {
                "upload_file_nm": "elife-95901-inf1.png",
                "href": "content/elife-95901-inf1.png",
            },
            {
                "upload_file_nm": "elife-95901-inf2.jpg",
                "href": "content/elife-95901-inf2.jpg",
            },
        ]
        # invoke
        result = peer_review.generate_new_image_file_paths(
            file_details_list,
            content_subfolder,
            identifier,
            caller_name,
            logger,
        )
        # assert
        self.assertEqual(len(result), 2)
        for index, file_details in enumerate(result):
            self.assertDictEqual(file_details, expected[index])
        self.assertEqual(
            logger.loginfo[-1],
            (
                "%s, for %s, file elife-95901-inf2.jpg new asset value"
                " content/elife-95901-inf2.jpg" % (caller_name, identifier)
            ),
        )
        self.assertEqual(
            logger.loginfo[-2],
            (
                "%s, for %s, file elife-95901-inf1.png new asset value"
                " content/elife-95901-inf1.png" % (caller_name, identifier)
            ),
        )


class TestModifyHrefToFileNameMap(unittest.TestCase):
    "tests for modify_href_to_file_name_map()"

    def test_modify_href_to_file_name_map(self):
        "test changing file path for image files in the map"
        href_to_file_name_map = {
            "https://i.imgur.com/vc4GR10.png": "tmp/2024-11-04.23.52.26/input_dir/vc4GR10.png",
            "https://i.imgur.com/FFeuydR.jpg": "tmp/2024-11-04.23.52.26/input_dir/FFeuydR.jpg",
        }
        file_details_list = [
            {
                "from_href": "https://i.imgur.com/vc4GR10.png",
                "upload_file_nm": "elife-95901-inf1.png",
            },
            {
                "from_href": "https://i.imgur.com/FFeuydR.jpg",
                "upload_file_nm": "elife-95901-inf2.jpg",
            },
        ]
        expected = {
            "https://i.imgur.com/vc4GR10.png": "elife-95901-inf1.png",
            "https://i.imgur.com/FFeuydR.jpg": "elife-95901-inf2.jpg",
        }
        # invoke
        peer_review.modify_href_to_file_name_map(
            href_to_file_name_map, file_details_list
        )
        # assert
        self.assertEqual(href_to_file_name_map, expected)


class TestMoveImages(unittest.TestCase):
    "tests for move_images()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_move_images(self):
        "test moving images files from input directory to output directory"
        directory = TempDirectory()
        # make output directory
        output_dir = os.path.join(directory.path, "content")
        os.mkdir(output_dir)
        # copy in test fixtures
        tmp_dir = os.path.join(directory.path, "tmp")
        os.mkdir(tmp_dir)
        for file_name in ["vc4GR10.png", "FFeuydR.jpg"]:
            with open(
                os.path.join(tmp_dir, file_name), "w", encoding="utf-8"
            ) as open_file:
                open_file.write("test_fixture")
        file_details_list = [
            {
                "from_href": "https://i.imgur.com/vc4GR10.png",
                "file_name": "%s/vc4GR10.png" % tmp_dir,
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf1.png",
                "id": "inf1",
                "href": "content/elife-95901-inf1.png",
            },
            {
                "from_href": "https://i.imgur.com/FFeuydR.jpg",
                "file_name": "%s/FFeuydR.jpg" % tmp_dir,
                "file_type": "figure",
                "upload_file_nm": "elife-95901-inf2.jpg",
                "id": "inf2",
                "href": "content/elife-95901-inf2.jpg",
            },
        ]
        to_dir = directory.path
        identifier = "10.7554/eLife.95901.1"
        caller_name = "MecaPeerReviewImages"
        logger = FakeLogger()
        # invoke
        peer_review.move_images(
            file_details_list, to_dir, identifier, caller_name, logger
        )
        # assert
        self.assertEqual(
            sorted(os.listdir(output_dir)),
            sorted(["elife-95901-inf1.png", "elife-95901-inf2.jpg"]),
        )


FIG_XML = (
    '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
    '<sub-article id="sa1">'
    "<body>"
    "<p>First paragraph.</p>"
    "<p><bold>Review image 1.</bold></p>"
    "<p>Caption title. Caption paragraph.</p>"
    '<p><inline-graphic xlink:href="local.jpg"/></p>'
    "</body>"
    "</sub-article>"
    '<sub-article id="sa2">'
    "<body>"
    "<p>First paragraph.</p>"
    "<p><bold>Review image 1.</bold></p>"
    "<p>Caption title. Caption paragraph.</p>"
    '<p><inline-graphic xlink:href="local2.jpg"/></p>'
    "<p>Paragraph.</p>"
    '<p><inline-graphic xlink:href="local3.jpg"/></p>'
    "<p><bold>Review image 2.</bold></p>"
    "<p>Caption title. Caption paragraph.</p>"
    '<p><inline-graphic xlink:href="local2.jpg"/></p>'
    "</body>"
    "</sub-article>"
    "</article>"
)


class TestGenerateFileTransformations(unittest.TestCase):
    "tests for generate_file_transformations()"

    def test_generate_file_transformations(self):
        "test finding inline-graphic files to be converted to fig graphics"
        xml_root = ElementTree.fromstring(FIG_XML)
        identifier = "10.7554/eLife.95901.1"
        caller_name = "MecaPeerReviewFigs"
        logger = FakeLogger()
        expected = [
            (
                ArticleZipFile("local.jpg", "None", "None"),
                ArticleZipFile("sa1-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig2.jpg", "None", "None"),
            ),
        ]
        # invoke
        result = peer_review.generate_file_transformations(
            xml_root, "fig", identifier, caller_name, logger
        )
        # assert
        self.assertEqual(len(result), len(expected))
        for result_index, result_file in enumerate(result):
            self.assertEqual(str(result_file), str(expected[result_index]))


class TestGenerateFigFileTransformations(unittest.TestCase):
    "tests for generate_fig_file_transformations()"

    def test_generate_fig_file_transformations(self):
        "test generating file transformation for fig graphics"
        xml_root = ElementTree.fromstring(FIG_XML)
        identifier = "10.7554/eLife.95901.1"
        caller_name = "fig_caller"
        logger = FakeLogger()
        expected = [
            (
                ArticleZipFile("local.jpg", "None", "None"),
                ArticleZipFile("sa1-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig2.jpg", "None", "None"),
            ),
        ]
        # invoke
        result = peer_review.generate_fig_file_transformations(
            xml_root, identifier, caller_name, logger
        )
        # assert
        self.assertEqual(len(result), len(expected))
        for result_index, result_file in enumerate(result):
            self.assertEqual(str(result_file), str(expected[result_index]))


class TestGenerateTableFileTransformations(unittest.TestCase):
    "tests for generate_table_file_transformations()"

    def test_generate_table_file_transformations(self):
        "test generating file transformation for table-wrap graphics"
        xml_root = ElementTree.fromstring(
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<sub-article id="sa1">'
            "<body>"
            "<p>First paragraph.</p>"
            "<p><bold>Review table 1.</bold></p>"
            "<p>Caption title. Caption paragraph.</p>"
            '<p><inline-graphic xlink:href="elife-95901-inf1.jpg"/></p>'
            "</body>"
            "</sub-article>"
            '<sub-article id="sa2">'
            "<body>"
            "<p>First paragraph.</p>"
            "<p><bold>Review table 1.</bold></p>"
            "<p>Caption title. Caption paragraph.</p>"
            '<p><inline-graphic xlink:href="local2.jpg"/></p>'
            "</body>"
            "</sub-article>"
            "</article>"
        )
        identifier = "10.7554/eLife.95901.1"
        caller_name = "table_caller"
        logger = FakeLogger()
        expected = [
            (
                ArticleZipFile("elife-95901-inf1.jpg", "None", "None"),
                ArticleZipFile("elife-95901-sa1-table1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-table1.jpg", "None", "None"),
            ),
        ]
        # invoke
        result = peer_review.generate_table_file_transformations(
            xml_root, identifier, caller_name, logger
        )
        # assert
        self.assertEqual(len(result), len(expected))
        for result_index, result_file in enumerate(result):
            self.assertEqual(str(result_file), str(expected[result_index]))


class TestGenerateEquationFileTransformations(unittest.TestCase):
    "tests for generate_equation_file_transformations()"

    def test_generate_equation_file_transformations(self):
        "test generating file transformation for disp-formula graphics"
        xml_root = ElementTree.fromstring(
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<sub-article id="sa1">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
            "</article>"
        )
        identifier = "10.7554/eLife.95901.1"
        caller_name = "table_caller"
        logger = FakeLogger()
        expected = [
            (
                ArticleZipFile("elife-inf2.jpg", "None", "None"),
                ArticleZipFile("elife-sa1-equ2.jpg", "None", "None"),
            ),
        ]
        # invoke
        result = peer_review.generate_equation_file_transformations(
            xml_root, identifier, caller_name, logger
        )
        # assert
        self.assertEqual(len(result), len(expected))
        for result_index, result_file in enumerate(result):
            self.assertEqual(str(result_file), str(expected[result_index]))


class TestGenerateInlineEquationFileTransformations(unittest.TestCase):
    "tests for generate_inline_equation_file_transformations()"

    def test_generate_inline_equation_file_transformations(self):
        "test generating file transformation for inline-formula graphics"
        xml_root = ElementTree.fromstring(
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<sub-article id="sa1">'
            "<body>"
            "<p>First paragraph with an inline equation"
            ' <inline-graphic xlink:href="elife-inf1.jpg"/>.</p>'
            "<p>Following is a display formula:</p>"
            '<p><inline-graphic xlink:href="elife-inf2.jpg"/></p>'
            "</body>"
            "</sub-article>"
            "</article>"
        )
        identifier = "10.7554/eLife.95901.1"
        caller_name = "table_caller"
        logger = FakeLogger()
        expected = [
            (
                ArticleZipFile("elife-inf1.jpg", "None", "None"),
                ArticleZipFile("elife-sa1-equ1.jpg", "None", "None"),
            ),
        ]
        # invoke
        result = peer_review.generate_inline_equation_file_transformations(
            xml_root, identifier, caller_name, logger
        )
        # assert
        self.assertEqual(len(result), len(expected))
        for result_index, result_file in enumerate(result):
            self.assertEqual(str(result_file), str(expected[result_index]))


class TestFilterTransformations(unittest.TestCase):
    "tests for filter_transformations()"

    def test_filter_transformations(self):
        "test filtering transformation list into copy file and rename files"
        file_transformations = [
            (
                ArticleZipFile("local.jpg", "None", "None"),
                ArticleZipFile("sa1-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig2.jpg", "None", "None"),
            ),
        ]
        expected_copy = [
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig2.jpg", "None", "None"),
            )
        ]
        expected_rename = [
            (
                ArticleZipFile("local.jpg", "None", "None"),
                ArticleZipFile("sa1-fig1.jpg", "None", "None"),
            ),
            (
                ArticleZipFile("local2.jpg", "None", "None"),
                ArticleZipFile("sa2-fig1.jpg", "None", "None"),
            ),
        ]
        # invoke
        (
            copy_file_transformations,
            rename_file_transformations,
        ) = peer_review.filter_transformations(file_transformations)
        # assert
        self.assertEqual(len(copy_file_transformations), 1)
        self.assertEqual(len(rename_file_transformations), 2)
        for index, transformation in enumerate(copy_file_transformations):
            self.assertEqual(str(transformation), str(expected_copy[index]))
        for index, transformation in enumerate(rename_file_transformations):
            self.assertEqual(str(transformation), str(expected_rename[index]))
