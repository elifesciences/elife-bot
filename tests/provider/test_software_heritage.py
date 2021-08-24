# coding=utf-8

import os
import unittest
from collections import OrderedDict
from xml.etree.ElementTree import Element
from mock import patch
from elifearticle import parse
from elifearticle.article import Article, Contributor
from provider import software_heritage, utils
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


def pretty_string(bytes):
    return str(bytes).replace("\\n", "\n")


class TestSoftwareHeritageProviderMetadata(unittest.TestCase):
    def setUp(self):
        self.file_name = "elife-15747-v1-era.zip"
        self.article, error_count = parse.build_article_from_xml(
            "tests/test_data/elife-15747-v2.xml", detail="full"
        )

    def test_metadata_xml(self):
        description = "A description & 0 < 1."
        create_origin_url = "https://elifesciences.org/articles/15747/executable"
        expected_xml_string = b"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0" xmlns:swhdeposit="https://www.softwareheritage.org/schema/2018/deposit">
    <title>Community-level cohesion without cooperation</title>
    <id>elife-15747-v1-era.zip</id>
    <swhdeposit:deposit>
        <swhdeposit:create_origin>
            <swhdeposit:origin url="https://elifesciences.org/articles/15747/executable"/>
        </swhdeposit:create_origin>
    </swhdeposit:deposit>
    <codemeta:description>A description &amp; 0 &lt; 1.</codemeta:description>
    <codemeta:referencePublication>
        <codemeta:name>Community-level cohesion without cooperation</codemeta:name>
        <codemeta:identifier>10.7554/eLife.15747</codemeta:identifier>
    </codemeta:referencePublication>
    <codemeta:license>
        <codemeta:url>http://creativecommons.org/licenses/by/4.0/</codemeta:url>
    </codemeta:license>
    <codemeta:author>
        <codemeta:name>Mikhail Tikhonov</codemeta:name>
        <codemeta:affiliation>Center of Mathematical Sciences and Applications, Harvard University, Cambridge, United States</codemeta:affiliation>
        <codemeta:affiliation>Harvard John A Paulson School of Engineering and Applied Sciences, Harvard University, Cambridge, United States</codemeta:affiliation>
        <codemeta:affiliation>Kavli Institute for Bionano Science and Technology, Harvard University, Cambridge, United States</codemeta:affiliation>
    </codemeta:author>
</entry>
"""
        metadata_object = software_heritage.metadata(self.file_name, self.article)
        metadata_object.codemeta["description"] = description
        metadata_object.swhdeposit["deposit"]["create_origin"][
            "url"
        ] = create_origin_url
        metadata_element = software_heritage.metadata_element(metadata_object)
        metadata_xml = software_heritage.metadata_xml(
            metadata_element, pretty=True, indent="    "
        )
        self.assertEqual(
            metadata_xml,
            expected_xml_string,
            "\n\n%s\n\nis not equal to expected\n\n%s"
            % (
                pretty_string(metadata_xml),
                pretty_string(expected_xml_string),
            ),
        )

    def test_metadata_xml_not_pretty(self):
        "test for non-pretty XML output"
        element = Element("root")
        expected = b'<?xml version="1.0" encoding="utf-8"?><root/>'
        self.assertEqual(software_heritage.metadata_xml(element), expected)

    def test_metadata_xml_contrib_collab(self):
        "test for group authors in collab tags and group member contributors"
        collab_contributor = Contributor("author", "", "", "Test Research Group")
        collab_contributor.group_author_key = "group1"
        group_member = Contributor("author", "Smith", "Chris")
        group_member.group_author_key = "group1"
        self.article.contributors.append(collab_contributor)
        self.article.contributors.append(group_member)
        metadata_object = software_heritage.metadata(self.file_name, self.article)
        expected = [
            OrderedDict(
                [
                    ("name", "Mikhail Tikhonov"),
                    (
                        "affiliations",
                        [
                            "Center of Mathematical Sciences and Applications, Harvard University, Cambridge, United States",
                            "Harvard John A Paulson School of Engineering and Applied Sciences, Harvard University, Cambridge, United States",
                            "Kavli Institute for Bionano Science and Technology, Harvard University, Cambridge, United States",
                        ],
                    ),
                ]
            ),
            OrderedDict([("name", "Test Research Group")]),
        ]
        self.assertEqual(metadata_object.codemeta["authors"], expected)


class TestSoftwareHeritageProviderReadme(unittest.TestCase):
    def test_readme(self):
        kwargs = {
            "article_title": "The eLife research article",
            "doi": "https://doi.org/10.7554/eLife.00666",
            "article_id": utils.pad_msid(666),
            "create_origin_url": "https://stencila.example.org/article-00666/",
            "content_license": "http://creativecommons.org/licenses/by/4.0/",
        }
        with open("tests/test_data/software_heritage/README.md", "r") as open_file:
            expected = open_file.read()
        readme_string = software_heritage.readme(kwargs)
        self.assertEqual(readme_string, expected)

    @patch.object(software_heritage, "Template")
    def test_readme_(self, mock_template):
        mock_template.return_value = None
        kwargs = {}
        readme_string = software_heritage.readme(kwargs)
        self.assertEqual(readme_string, "")


class TestDisplayToOrigin(unittest.TestCase):
    def test_display_to_origin_none(self):
        display = None
        self.assertIsNone(software_heritage.display_to_origin(display))

    def test_display_to_origin_general(self):
        display = "https://example.org"
        self.assertEqual(software_heritage.display_to_origin(display), display)

    def test_display_to_origin_era(self):
        display = "https://elife.stencila.io/article-30274/"
        self.assertEqual(software_heritage.display_to_origin(display), display)

    def test_display_to_origin_era_with_version(self):
        display = "https://elife.stencila.io/article-30274/v99/"
        expected = "https://elife.stencila.io/article-30274/"
        self.assertEqual(software_heritage.display_to_origin(display), expected)


class TestSWHPostRequest(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.zip_file_name = "elife-30274-v1-era.zip"
        self.atom_file_name = "elife-30274-v1-era.xml"
        folder_path = os.path.join(
            "tests",
            "files_source",
            "software_heritage",
            "run",
            "cf9c7e86-7355-4bb4-b48e-0bc284221251/",
        )
        self.zip_file_path = os.path.join(folder_path, self.zip_file_name)
        self.atom_file_path = os.path.join(folder_path, self.atom_file_name)

    @patch("requests.post")
    def test_swh_post_request_201(self, mock_requests_post):
        url = "https://example.org/"
        response_content = (
            '<entry><link rel="edit-media" href="/1/hal/10/media/"/></entry>'
        )
        response = FakeResponse(201)
        response.content = response_content
        mock_requests_post.return_value = response
        response = software_heritage.swh_post_request(
            url,
            settings_mock.software_heritage_auth_user,
            settings_mock.software_heritage_auth_pass,
            self.zip_file_path,
            self.atom_file_path,
            in_progress=False,
            logger=self.logger,
        )
        self.assertEqual(
            self.logger.loginfo[-1], "Response from SWH API: 201\n%s" % response_content
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "Post zip file %s, atom file %s to SWH API: POST %s"
            % (self.zip_file_name, self.atom_file_name, url),
        )

    @patch("requests.post")
    def test_swh_post_request_201_zip_only(self, mock_requests_post):
        url = "https://example.org/"
        response_content = (
            '<entry><link rel="edit-media" href="/1/hal/10/media/"/></entry>'
        )
        response = FakeResponse(201)
        response.content = response_content
        mock_requests_post.return_value = response
        response = software_heritage.swh_post_request(
            url,
            settings_mock.software_heritage_auth_user,
            settings_mock.software_heritage_auth_pass,
            self.zip_file_path,
            None,
            in_progress=False,
            logger=self.logger,
        )
        self.assertEqual(
            self.logger.loginfo[-1], "Response from SWH API: 201\n%s" % response_content
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "Post zip file %s to SWH API: POST %s" % (self.zip_file_name, url),
        )

    @patch("requests.post")
    def test_swh_post_request_412(self, mock_requests_post):
        url = "https://example.org/"
        response = FakeResponse(412)
        response.content = ""
        mock_requests_post.return_value = response

        with self.assertRaises(Exception) as test_exception:
            response = software_heritage.swh_post_request(
                url,
                settings_mock.software_heritage_auth_user,
                settings_mock.software_heritage_auth_pass,
                self.zip_file_path,
                self.atom_file_path,
                in_progress=False,
                logger=self.logger,
            )

        self.assertEqual(
            str(test_exception.exception),
            "Error posting zip file %s and atom file %s to SWH API: 412\n"
            % (self.zip_file_name, self.atom_file_name),
        )


class TestSWHOriginExists(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url_pattern = settings_mock.software_heritage_api_get_origin_pattern
        self.origin = "https://stencila.example.org/article-00666/"

    @patch("requests.head")
    def test_swh_origin_exists_200(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(200)
        origin_exists = software_heritage.swh_origin_exists(
            self.url_pattern, self.origin, logger=self.logger
        )
        self.assertEqual(origin_exists, True)
        self.assertEqual(
            self.logger.loginfo[-1],
            "Returning SWH origin exists value of True for origin %s" % self.origin,
        )
        self.assertEqual(self.logger.loginfo[-2], "SWH origin status code 200")
        self.assertEqual(
            self.logger.loginfo[-3],
            "Checking if SWH origin exists at API URL %s"
            % self.url_pattern.format(origin=self.origin),
        )

    @patch("requests.head")
    def test_swh_origin_exists_404(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(404)
        origin_exists = software_heritage.swh_origin_exists(
            self.url_pattern, self.origin, logger=self.logger
        )
        self.assertEqual(origin_exists, False)

    @patch("requests.head")
    def test_swh_origin_exists_500(self, mock_requests_head):
        mock_requests_head.return_value = FakeResponse(500)
        origin_exists = software_heritage.swh_origin_exists(
            self.url_pattern, self.origin, logger=self.logger
        )
        self.assertEqual(origin_exists, None)
