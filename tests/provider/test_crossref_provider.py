import os
import time
import unittest
from collections import OrderedDict
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
from elifecrossref import generate
from elifearticle.article import Article, ArticleDate, Contributor
from provider import crossref
from tests import settings_mock
import tests.test_data as test_case_data
from tests.activity.classes_mock import FakeLogger, FakeResponse


def expected_http_detail(file_name, status_code):
    return [
        "XML file: " + file_name,
        "HTTP status: " + str(status_code),
        "HTTP response: ",
    ]


class TestCrossrefProvider(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.good_xml_file = "tests/test_data/crossref/outbox/elife-18753-v1.xml"
        self.bad_xml_file = "tests/test_data/activity.json"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_elifecrossref_config(self):
        """test reading the crossref config file"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        self.assertIsNotNone(crossref_config)

    def test_parse_article_xml(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        self.assertEqual(len(articles), 1)

    def test_parse_article_xml_exception(self):
        articles = crossref.parse_article_xml([self.bad_xml_file], self.directory.path)
        self.assertEqual(len(articles), 0)

    def test_article_xml_list_parse(self):
        article_xml_files = [self.good_xml_file, self.bad_xml_file]
        bad_xml_files = []
        article_object_map = crossref.article_xml_list_parse(
            article_xml_files, bad_xml_files, self.directory.path
        )
        # one good article in the map, one bad xml file in the bad_xml_files list
        self.assertEqual(len(article_object_map), 1)
        self.assertEqual(len(bad_xml_files), 1)

    def test_contributor_orcid_authenticated(self):
        "test setting Contributor orcid_authenticated attribute"
        article = Article()
        contributor = Contributor("author", "Surname", "Given")
        article.add_contributor(contributor)
        article = crossref.contributor_orcid_authenticated(article, True)
        self.assertEqual(article.contributors[0].orcid_authenticated, True)

    @patch("provider.lax_provider.article_versions")
    def test_set_article_pub_date(self, mock_article_versions):
        """test for when the date is missing and uses lax data"""
        mock_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # reset the dates
        article.dates = {}
        # now set the date
        crossref.set_article_pub_date(
            article, crossref_config, settings_mock, FakeLogger()
        )
        self.assertEqual(len(article.dates), 1)

    def test_set_article_version(self):
        """test version when it is already present"""
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # set the version but it is already set
        crossref.set_article_version(article, settings_mock)
        self.assertEqual(article.version, 1)

    @patch("provider.lax_provider.article_versions")
    def test_set_article_version_missing(self, mock_article_versions):
        """test setting version when missing"""
        mock_article_versions.return_value = (
            200,
            test_case_data.lax_article_versions_response_data,
        )
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # reset the version
        article.version = None
        # now set the version
        crossref.set_article_version(article, settings_mock)
        self.assertEqual(article.version, 3)

    def test_article_first_pub_date(self):
        """test finding a pub date in the article dates"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # get the pub date
        pub_date_object = crossref.article_first_pub_date(crossref_config, article)
        expected_date = time.strptime("2016-07-15 UTC", "%Y-%m-%d %Z")
        self.assertEqual(pub_date_object.date_type, "pub")
        self.assertEqual(pub_date_object.date, expected_date)

    def test_approve_to_generate(self):
        """test approving based on the pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    @patch("time.gmtime")
    def test_approve_to_generate_not_approved(self, mock_gmtime):
        """test approving if the pub date is after the mock current date"""
        mock_gmtime.return_value = (1, 1, 1, 1, 1, 1, 1, 1, 0)
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertFalse(approved)

    def test_approve_to_generate_no_date(self):
        """test approving when there is no pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article = articles[0]
        # reset the dates
        article.dates = {}
        approved = crossref.approve_to_generate(crossref_config, article)
        self.assertTrue(approved)

    def test_approve_to_generate_list(self):
        """test approving a list of files based on the pub date"""
        crossref_config = crossref.elifecrossref_config(settings_mock)
        # build an article
        article = crossref.parse_article_xml([self.good_xml_file], self.directory.path)[
            0
        ]
        # make a fake article with a future pub date
        future_article = crossref.parse_article_xml(
            [self.good_xml_file], self.directory.path
        )[0]
        future_date = ArticleDate("pub", time.strptime("2999-07-15 UTC", "%Y-%m-%d %Z"))
        future_article.dates = {}
        future_article.add_date(future_date)
        # assemble the map of article objects
        article_object_map = OrderedDict(
            [(self.good_xml_file, article), ("future_article.xml", future_article)]
        )
        bad_xml_files = []
        approved = crossref.approve_to_generate_list(
            article_object_map, crossref_config, bad_xml_files
        )
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(bad_xml_files), 1)

    def test_crossref_data_payload(self):
        expected = {
            "operation": "doMDUpload",
            "login_id": settings_mock.crossref_login_id,
            "login_passwd": settings_mock.crossref_login_passwd,
        }
        payload = crossref.crossref_data_payload(
            settings_mock.crossref_login_id, settings_mock.crossref_login_passwd
        )
        self.assertEqual(payload, expected)

    @patch("requests.post")
    def test_upload_files_to_endpoint(self, fake_request):
        status_code = 200
        xml_files = [self.good_xml_file]

        fake_request.return_value = FakeResponse(status_code)

        expected_status = True
        expected_detail = expected_http_detail(self.good_xml_file, status_code)

        status, http_detail_list = crossref.upload_files_to_endpoint("", "", xml_files)
        self.assertEqual(status, expected_status)
        self.assertEqual(http_detail_list, expected_detail)

    @patch("requests.post")
    def test_upload_files_to_endpoint_failure(self, fake_request):
        status_code = 500
        xml_files = [self.good_xml_file]

        fake_request.return_value = FakeResponse(status_code)

        expected_status = False
        expected_detail = expected_http_detail(self.good_xml_file, status_code)

        status, http_detail_list = crossref.upload_files_to_endpoint("", "", xml_files)
        self.assertEqual(status, expected_status)
        self.assertEqual(http_detail_list, expected_detail)

    def test_generate_crossref_xml_to_disk(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article_object_map = OrderedDict(
            [
                (self.good_xml_file, articles[0]),
                ("fake_file_will_raise_exception.xml", None),
            ]
        )
        good_xml_files = []
        bad_xml_files = []
        crossref_config = crossref.elifecrossref_config(settings_mock)
        result = crossref.generate_crossref_xml_to_disk(
            article_object_map, crossref_config, good_xml_files, bad_xml_files
        )
        self.assertTrue(result)
        self.assertEqual(len(good_xml_files), 1)
        self.assertEqual(len(bad_xml_files), 1)


class TestBuildCrossrefXml(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.good_xml_file = "tests/test_data/crossref/outbox/elife-18753-v1.xml"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_build_crossref_xml(self):
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article_object_map = OrderedDict([(self.good_xml_file, articles[0])])
        good_xml_files = []
        bad_xml_files = []
        crossref_config = crossref.elifecrossref_config(settings_mock)
        result = crossref.build_crossref_xml(
            article_object_map, crossref_config, good_xml_files, bad_xml_files
        )
        self.assertTrue(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(good_xml_files), 1)
        self.assertEqual(len(bad_xml_files), 0)

    @patch.object(generate, "build_crossref_xml")
    def test_build_crossref_xml_exception(self, mock_build):
        "raise an exception when building object"
        mock_build.side_effect = Exception("An exception")
        articles = crossref.parse_article_xml([self.good_xml_file], self.directory.path)
        article_object_map = OrderedDict([(self.good_xml_file, articles[0])])
        good_xml_files = []
        bad_xml_files = []
        crossref_config = crossref.elifecrossref_config(settings_mock)
        result = crossref.build_crossref_xml(
            article_object_map, crossref_config, good_xml_files, bad_xml_files
        )
        self.assertEqual(len(result), 0)
        self.assertEqual(len(good_xml_files), 0)
        self.assertEqual(len(bad_xml_files), 1)


class TestAddRelProgramTag(unittest.TestCase):
    def setUp(self):
        ElementTree.register_namespace("rel", "http://www.crossref.org/relations.xsd")
        self.xml_header = (
            b'<doi_batch xmlns:rel="http://www.crossref.org/relations.xsd">'
            b"<body><journal><journal_article>"
        )
        self.xml_footer = b"</journal_article></journal></body></doi_batch>"

    def test_add_rel_program_tag(self):
        "test adding rel:program tag to journal_article tag"
        xml_string = self.xml_header + self.xml_footer
        root = ElementTree.fromstring(xml_string)
        # check rel:program is in XML prior to the function invocation
        self.assertTrue(b"<rel:program" not in ElementTree.tostring(root))
        # invoke function
        crossref.add_rel_program_tag(root)
        # assert rel:program tag is present
        self.assertTrue(b"<rel:program />" in ElementTree.tostring(root))

    def test_add_rel_program_tag_already_present(self):
        "test adding rel:program tag if it is already there"
        xml_string = self.xml_header + b"<rel:program/>" + self.xml_footer
        root = ElementTree.fromstring(xml_string)
        # check rel:program is in XML prior to the function invocation
        self.assertTrue(b"<rel:program" in ElementTree.tostring(root))
        # invoke function
        crossref.add_rel_program_tag(root)
        # assert rel:program tag is present
        self.assertTrue(b"<rel:program />" in ElementTree.tostring(root))
        # assert only one tag is present
        self.assertEqual(ElementTree.tostring(root).count(b"<rel:program />"), 1)


class TestClearRelProgramTag(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_clear_rel_program_tag(self):
        xml_file = "tests/test_data/crossref_minimal/outbox/elife-1234567890-v99.xml"
        articles = crossref.parse_article_xml([xml_file], self.directory.path)
        article_object_map = OrderedDict([(xml_file, articles[0])])
        crossref_config = crossref.elifecrossref_config(settings_mock)
        object_list = crossref.build_crossref_xml(
            article_object_map, crossref_config, [], []
        )
        crossref_xml_object = object_list[0]
        # check rel:program is in XML prior to the function invocation
        self.assertTrue("<rel:program" in crossref_xml_object.output_xml())
        self.assertTrue("<rel:related_item>" in crossref_xml_object.output_xml())
        # invoke function
        crossref.clear_rel_program_tag(crossref_xml_object)
        # assert rel:program tag is empty
        self.assertTrue("<rel:program/>" in crossref_xml_object.output_xml())
        # assert rel:program child tag is not present
        self.assertTrue("<rel:related_item>" not in crossref_xml_object.output_xml())


class TestAddIsSameAsTag(unittest.TestCase):
    def setUp(self):
        ElementTree.register_namespace("rel", "http://www.crossref.org/relations.xsd")

    def test_add_is_same_as_tag(self):
        xml_string = b'<rel:program xmlns:rel="http://www.crossref.org/relations.xsd"/>'
        root = ElementTree.fromstring(xml_string)
        doi = "10.7554/eLife.1234567890"
        expected = (
            b'<rel:program xmlns:rel="http://www.crossref.org/relations.xsd">'
            b"<rel:related_item>"
            b'<rel:intra_work_relation identifier-type="doi" relationship-type="isSameAs">'
            b"10.7554/eLife.1234567890"
            b"</rel:intra_work_relation>"
            b"</rel:related_item>"
            b"</rel:program>"
        )
        # invoke function
        crossref.add_is_same_as_tag(root, doi)
        # assert
        self.assertEqual(ElementTree.tostring(root), expected)


class TestAddIsVersionOfTag(unittest.TestCase):
    def setUp(self):
        ElementTree.register_namespace("rel", "http://www.crossref.org/relations.xsd")

    def test_add_is_version_of_tag(self):
        xml_string = b'<rel:program xmlns:rel="http://www.crossref.org/relations.xsd"/>'
        root = ElementTree.fromstring(xml_string)
        doi = "10.7554/eLife.1234567890"
        expected = (
            b'<rel:program xmlns:rel="http://www.crossref.org/relations.xsd">'
            b"<rel:related_item>"
            b'<rel:intra_work_relation identifier-type="doi" relationship-type="isVersionOf">'
            b"10.7554/eLife.1234567890"
            b"</rel:intra_work_relation>"
            b"</rel:related_item>"
            b"</rel:program>"
        )
        # invoke function
        crossref.add_is_version_of_tag(root, doi)
        # assert
        self.assertEqual(ElementTree.tostring(root), expected)


class TestCrossrefXmlToDisk(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_crossref_xml_to_disk(self):
        xml_file = "tests/test_data/crossref_minimal/outbox/elife-1234567890-v99.xml"
        articles = crossref.parse_article_xml([xml_file], self.directory.path)
        article_object_map = OrderedDict([(xml_file, articles[0])])
        crossref_config = crossref.elifecrossref_config(settings_mock)
        object_list = crossref.build_crossref_xml(
            article_object_map, crossref_config, [], []
        )
        crossref_xml_object = object_list[0]
        # invoke function
        crossref.crossref_xml_to_disk(crossref_xml_object, self.directory.path)
        # assertion
        file_list = os.listdir(self.directory.path)
        self.assertEqual(len(file_list), 1)
        self.assertTrue(file_list[0].endswith(".xml"))


class TestDoiExists(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.doi = "10.7554/eLife.99999"

    @patch("requests.head")
    def test_doi_exists_302(self, fake_request):
        fake_request.return_value = FakeResponse(302)
        self.assertTrue(crossref.doi_exists(self.doi, self.logger))

    @patch("requests.head")
    def test_doi_exists_404(self, fake_request):
        fake_request.return_value = FakeResponse(404)
        self.assertFalse(crossref.doi_exists(self.doi, self.logger))

    @patch("requests.head")
    def test_doi_exists_200(self, fake_request):
        fake_request.return_value = FakeResponse(200)
        self.assertFalse(crossref.doi_exists(self.doi, self.logger))
        self.assertEqual(
            self.logger.loginfo[-1], "Status code for 10.7554/eLife.99999 was 200"
        )


class TestDoiDoesNotExist(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.doi = "10.7554/eLife.99999"

    @patch("requests.head")
    def test_doi_does_not_exist_302(self, fake_request):
        fake_request.return_value = FakeResponse(302)
        self.assertFalse(crossref.doi_does_not_exist(self.doi, self.logger))

    @patch("requests.head")
    def test_doi_does_not_exist_404(self, fake_request):
        fake_request.return_value = FakeResponse(404)
        self.assertTrue(crossref.doi_does_not_exist(self.doi, self.logger))

    @patch("requests.head")
    def test_doi_does_not_exist_200(self, fake_request):
        fake_request.return_value = FakeResponse(200)
        self.assertFalse(crossref.doi_does_not_exist(self.doi, self.logger))

    @patch("requests.head")
    def test_doi_does_not_exist_500(self, fake_request):
        fake_request.return_value = FakeResponse(500)
        self.assertIsNone(crossref.doi_does_not_exist(self.doi, self.logger))
