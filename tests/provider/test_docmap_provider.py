import json
import unittest
from mock import patch
from docmaptools import parse
from provider import docmap_provider
from tests import read_fixture, settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


ELIFE_DOCMAP = {"publisher": {"account": {"id": "https://sciety.org/groups/elife"}}}
NON_ELIFE_DOCMAP = {"publisher": {"account": {"id": "https://example.org"}}}


class TestDocmapIndexUrl(unittest.TestCase):
    def test_docmap_index_url(self):
        result = docmap_provider.docmap_index_url(settings_mock)
        expected = "https://example.org/path/index"
        self.assertEqual(result, expected)

    def test_docmap_index_url_no_settings(self):
        class FakeSettings:
            pass

        result = docmap_provider.docmap_index_url(FakeSettings())
        expected = None
        self.assertEqual(result, expected)


class TestGetDocmapIndex(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url = "https://example.org/"

    @patch("requests.get")
    def test_get_docmap_index_200(self, mock_requests_get):
        content = b"test"
        status_code = 200
        user_agent = settings_mock.user_agent
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = docmap_provider.get_docmap_index(
            self.url,
            self.logger,
            user_agent=user_agent,
        )
        self.assertEqual(result, content)

    @patch("requests.get")
    def test_get_docmap_index_404(self, mock_requests_get):
        status_code = 404
        mock_requests_get.return_value = FakeResponse(status_code)
        with self.assertRaises(Exception):
            docmap_provider.get_docmap_index(self.url, self.logger)


class TestGetDocmapIndexByAccountId(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.url = "https://example.org/"

    @patch("requests.get")
    def test_get_docmap_index_by_account_id_blank(self, mock_requests_get):
        "test for non-list JSON returned"
        content = b""
        status_code = 200
        user_agent = settings_mock.user_agent
        expected = None
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = docmap_provider.get_docmap_index_by_account_id(
            self.url,
            settings_mock.docmap_account_id,
            self.logger,
            user_agent=user_agent,
        )
        self.assertEqual(result, expected)

    @patch("requests.get")
    def test_get_docmap_index_by_account_id_empty(self, mock_requests_get):
        "test for non-list JSON returned"
        content = b"{}"
        status_code = 200
        expected = None
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = docmap_provider.get_docmap_index_by_account_id(
            self.url, settings_mock.docmap_account_id, self.logger
        )
        self.assertEqual(result, expected)

    @patch("requests.get")
    def test_get_docmap_index_by_account_id_list_content(self, mock_requests_get):
        "test for when a list of values is returned"
        content = b'{"docmaps": [%s, %s]}' % (
            json.dumps(NON_ELIFE_DOCMAP).encode("utf-8"),
            json.dumps(ELIFE_DOCMAP).encode("utf-8"),
        )
        status_code = 200
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        result = docmap_provider.get_docmap_index_by_account_id(
            self.url, settings_mock.docmap_account_id, self.logger
        )
        self.assertEqual(json.dumps(result.get("docmaps")[0]), json.dumps(ELIFE_DOCMAP))


class TestGetDocmapIndexJson(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    @patch("requests.get")
    def test_get_docmap_index(self, mock_requests_get):
        "test basic content in the endpoint response"
        caller_name = "FindNewDocmaps"
        content = b'{"docmaps": [%s, %s]}' % (
            json.dumps(NON_ELIFE_DOCMAP).encode("utf-8"),
            json.dumps(ELIFE_DOCMAP).encode("utf-8"),
        )
        status_code = 200
        expected = {"docmaps": [ELIFE_DOCMAP]}
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        # invoke
        result = docmap_provider.get_docmap_index_json(
            settings_mock, caller_name, self.logger
        )
        # assert
        self.assertEqual(result, expected)
        self.assertEqual(
            self.logger.loginfo[1],
            "%s, docmap_endpoint_url: %s"
            % (caller_name, settings_mock.docmap_index_url),
        )
        self.assertEqual(
            self.logger.loginfo[2],
            "%s, getting docmap index string" % caller_name,
        )

    @patch("requests.get")
    def test_get_docmap_index_empty(self, mock_requests_get):
        "test empty list of docmaps in the endpoint response"
        caller_name = "FindNewDocmaps"
        content = b'{"docmaps": [{}]}'
        status_code = 200
        expected = {"docmaps": []}
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        # invoke
        result = docmap_provider.get_docmap_index_json(
            settings_mock, caller_name, self.logger
        )
        # assert
        self.assertEqual(result, expected)

    @patch("requests.get")
    def test_get_docmap_index_json_blank(self, mock_requests_get):
        "test if the endpoint content is blank"
        caller_name = "FindNewDocmaps"
        content = b"{}"
        status_code = 200
        expected = None
        mock_requests_get.return_value = FakeResponse(status_code, content=content)
        # invoke
        result = docmap_provider.get_docmap_index_json(
            settings_mock, caller_name, self.logger
        )
        # assert
        self.assertEqual(result, expected)


class TestProfileDocmapSteps(unittest.TestCase):
    "tests for profile_docmap_steps()"

    def test_all(self):
        "test an example with all the data"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        step_map = parse.preprint_version_doi_step_map(docmap_json)
        docmap_steps_value = step_map.get("10.7554/eLife.87445.1")
        expected = {"computer-file-count": 1, "peer-review-count": 4}
        result = docmap_provider.profile_docmap_steps(docmap_steps_value)
        self.assertEqual(result, expected)

    def test_none(self):
        "test None value"
        docmap_steps_value = None
        expected = {"computer-file-count": 0, "peer-review-count": 0}
        result = docmap_provider.profile_docmap_steps(docmap_steps_value)
        self.assertEqual(result, expected)


class TestChangedVersionDoiList(unittest.TestCase):
    "tests for changed_version_doi_list()"

    def test_changed_version_doi_list(self):
        "test by loading some test fixture data"
        expected = ["10.7554/eLife.84364.1", "10.7554/eLife.87445.2"]
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        # load and modify data to be the previous JSON
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del prev_docmap_json["steps"]["_:b3"]
        del prev_docmap_json["steps"]["_:b4"]
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_not_in_previous_list(self):
        "test if the version DOI in the current list does not appear in the previous list"
        expected = [
            "10.7554/eLife.84364.1",
            "10.7554/eLife.87445.1",
            "10.7554/eLife.87445.2",
        ]
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        prev_docmap_index_json = {"docmaps": []}

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_previous_json_none(self):
        "test if previous JSON is None"
        expected = [
            "10.7554/eLife.84364.1",
            "10.7554/eLife.87445.1",
            "10.7554/eLife.87445.2",
        ]
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_previous_json_none_no_new_json(self):
        "test if previous JSON is None and no data in new JSON"
        expected = []
        docmap_index_json = {"docmaps": [ELIFE_DOCMAP]}
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_peer_review_added(self):
        "test if a peer review is added"
        expected = [
            "10.7554/eLife.84364.1",
        ]
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
            ]
        }
        # load and modify data to be the previous JSON
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_84364.json"))
        del prev_docmap_json["steps"]["_:b1"]["actions"][-1]
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_not_changed(self):
        "test if the JSON is unchanged between previous and current run"
        expected = []
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
            ]
        }
        # load previous JSON with the same data
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_84364.json"))
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)

    def test_no_computer_file(self):
        "test if the"
        expected = ["10.7554/eLife.87445.1"]
        # delete computer-file data
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del docmap_json["steps"]["_:b3"]["inputs"][0]["content"]
        docmap_index_json = {"docmaps": [docmap_json]}
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_list(
            docmap_index_json, prev_docmap_index_json
        )
        self.assertEqual(result, expected)
