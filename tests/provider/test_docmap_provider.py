import json
import unittest
import datetime
from mock import patch
from docmaptools import parse
from provider import docmap_provider, utils
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


class TestComputerFiles(unittest.TestCase):
    "tests for computer_files()"

    def test_computer_files(self):
        "test get list of computer-file inputs from docmap steps"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        step_map = parse.preprint_version_doi_step_map(docmap_json)
        docmap_steps_value = step_map.get("10.7554/eLife.87445.1")
        step = docmap_steps_value[0]
        expected = [
            {
                "type": "computer-file",
                "url": (
                    "s3://transfers-elife/biorxiv_Current_Content/March_2023/"
                    "16_Mar_23_Batch_1553/8cd2942b-6c47-1014-bdbd-e77a5e155f8d.meca"
                ),
            }
        ]
        result = docmap_provider.computer_files(step)
        self.assertEqual(result, expected)


class TestOutputComputerFiles(unittest.TestCase):
    "tests for output_computer_files()"

    def test_output_computer_files(self):
        "test get list of computer-file from docmap output steps"
        docmap_json = json.loads(read_fixture("sample_docmap_for_95901.json"))
        step_map = parse.preprint_version_doi_step_map(docmap_json)
        docmap_steps_value = step_map.get("10.7554/eLife.95901.1")
        step = docmap_steps_value[1]
        expected = [
            {
                "type": "computer-file",
                "url": "s3://prod-elife-epp-meca/reviewed-preprints/95901-v1-meca.zip",
            }
        ]
        result = docmap_provider.output_computer_files(step)
        self.assertEqual(result, expected)


class TestProfileDocmapSteps(unittest.TestCase):
    "tests for profile_docmap_steps()"

    def test_all(self):
        "test an example with all the data"
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        step_map = parse.preprint_version_doi_step_map(docmap_json)
        docmap_steps_value = step_map.get("10.7554/eLife.87445.1")
        expected = {
            "computer-file-count": 1,
            "peer-review-count": 4,
            "published": "2023-05-12T14:00:00+00:00",
        }
        result = docmap_provider.profile_docmap_steps(docmap_steps_value)
        self.assertEqual(result, expected)

    def test_none(self):
        "test None value"
        docmap_steps_value = None
        expected = {"computer-file-count": 0, "peer-review-count": 0, "published": None}
        result = docmap_provider.profile_docmap_steps(docmap_steps_value)
        self.assertEqual(result, expected)


class TestChangedVersionDoiData(unittest.TestCase):
    "tests for changed_version_doi_data()"

    def setUp(self):
        self.logger = FakeLogger()
        # date in past
        self.past_date = datetime.datetime.strptime(
            "1970-01-01T23:45:00+00:00", "%Y-%m-%dT%H:%M:%S%z"
        )
        # date in future
        self.future_date = datetime.datetime.strptime(
            "2424-01-01T23:45:00+00:00", "%Y-%m-%dT%H:%M:%S%z"
        )

    @patch.object(utils, "get_current_datetime")
    def test_changed_version_doi_data(self, fake_get_current_datetime):
        "test by loading some test fixture data"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": [
                "10.7554/eLife.84364.1",
                "10.7554/eLife.87445.2",
            ],
            "new_version_doi_list": ["10.7554/eLife.84364.1", "10.7554/eLife.84364.2"],
            "no_computer_file_version_doi_list": ["10.7554/eLife.84364.2"],
        }
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

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_not_in_previous_list(self, fake_get_current_datetime):
        "test if the version DOI in the current list does not appear in the previous list"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": [
                "10.7554/eLife.84364.1",
                "10.7554/eLife.87445.1",
                "10.7554/eLife.87445.2",
            ],
            "new_version_doi_list": [
                "10.7554/eLife.84364.1",
                "10.7554/eLife.84364.2",
                "10.7554/eLife.87445.1",
                "10.7554/eLife.87445.2",
            ],
            "no_computer_file_version_doi_list": ["10.7554/eLife.84364.2"],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        prev_docmap_index_json = {"docmaps": []}
        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_previous_json_none(self, fake_get_current_datetime):
        "test if previous JSON is None"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": [
                "10.7554/eLife.84364.1",
                "10.7554/eLife.87445.1",
                "10.7554/eLife.87445.2",
            ],
            "new_version_doi_list": [
                "10.7554/eLife.84364.1",
                "10.7554/eLife.84364.2",
                "10.7554/eLife.87445.1",
                "10.7554/eLife.87445.2",
            ],
            "no_computer_file_version_doi_list": ["10.7554/eLife.84364.2"],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_previous_json_none_no_new_json(self, fake_get_current_datetime):
        "test if previous JSON is None and no data in new JSON"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": [],
            "new_version_doi_list": [],
            "no_computer_file_version_doi_list": [],
        }
        docmap_index_json = {"docmaps": [ELIFE_DOCMAP]}
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_peer_review_added(self, fake_get_current_datetime):
        "test if a peer review is added"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": ["10.7554/eLife.84364.1"],
            "new_version_doi_list": [],
            "no_computer_file_version_doi_list": [],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
            ]
        }
        # load and modify data to be the previous JSON
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_84364.json"))
        del prev_docmap_json["steps"]["_:b1"]["actions"][-1]
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}
        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_not_changed(self, fake_get_current_datetime):
        "test if the JSON is unchanged between previous and current run"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": [],
            "new_version_doi_list": [],
            "no_computer_file_version_doi_list": [],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_84364.json")),
            ]
        }
        # load previous JSON with the same data
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_84364.json"))
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_no_computer_file(self, fake_get_current_datetime):
        "test if there is no computer-file"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": ["10.7554/eLife.87445.1"],
            "new_version_doi_list": ["10.7554/eLife.87445.1", "10.7554/eLife.87445.2"],
            "no_computer_file_version_doi_list": ["10.7554/eLife.87445.2"],
        }
        # delete computer-file data
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del docmap_json["steps"]["_:b3"]["inputs"][0]["content"]
        docmap_index_json = {"docmaps": [docmap_json]}
        prev_docmap_index_json = None

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_computer_file_is_added(self, fake_get_current_datetime):
        "test if previous docmap has no computer-file and the current docmap does have one"
        fake_get_current_datetime.return_value = self.past_date
        expected = {
            "ingest_version_doi_list": ["10.7554/eLife.87445.2"],
            "new_version_doi_list": [],
            "no_computer_file_version_doi_list": [],
        }
        docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        docmap_index_json = {"docmaps": [docmap_json]}
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        # delete computer-file data from previous docmap
        del prev_docmap_json["steps"]["_:b3"]["inputs"][0]["content"]
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}

        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)

    @patch.object(utils, "get_current_datetime")
    def test_past_published_date(self, fake_get_current_datetime):
        "test if the published date is far in the past"
        fake_get_current_datetime.return_value = self.future_date
        expected = {
            "ingest_version_doi_list": [],
            "new_version_doi_list": [],
            "no_computer_file_version_doi_list": [],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        # load and modify data to be the previous JSON
        prev_docmap_json = json.loads(read_fixture("sample_docmap_for_87445.json"))
        del prev_docmap_json["steps"]["_:b3"]
        del prev_docmap_json["steps"]["_:b4"]
        prev_docmap_index_json = {"docmaps": [prev_docmap_json]}
        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "DOI 10.7554/eLife.87445.2 omitted, "
                "its published date 2023-11-22T14:00:00+00:00 is too far in the past"
            ),
        )

    @patch.object(utils, "get_current_datetime")
    def test_past_published_date_no_previous(self, fake_get_current_datetime):
        "test if the published date is far in the past and no previous docmap was stored"
        fake_get_current_datetime.return_value = self.future_date
        expected = {
            "ingest_version_doi_list": [],
            "new_version_doi_list": ["10.7554/eLife.87445.1", "10.7554/eLife.87445.2"],
            "no_computer_file_version_doi_list": [],
        }
        docmap_index_json = {
            "docmaps": [
                json.loads(read_fixture("sample_docmap_for_87445.json")),
            ]
        }
        prev_docmap_index_json = None
        result = docmap_provider.changed_version_doi_data(
            docmap_index_json, prev_docmap_index_json, self.logger
        )
        self.assertDictEqual(result, expected)
        self.assertEqual(
            self.logger.loginfo[-1],
            (
                "DOI 10.7554/eLife.87445.2 omitted, "
                "its published date 2023-11-22T14:00:00+00:00 is too far in the past"
            ),
        )


class TestCheckPublishedDate(unittest.TestCase):
    "tests for check_published_date()"

    def setUp(self):
        # date in past
        self.past_date_string = "1970-01-01T23:45:00+00:00"
        self.past_date = datetime.datetime.strptime(
            self.past_date_string, "%Y-%m-%dT%H:%M:%S%z"
        )
        # date in future
        self.future_date_string = "2424-01-01T23:45:00+00:00"
        self.future_date = datetime.datetime.strptime(
            self.future_date_string, "%Y-%m-%dT%H:%M:%S%z"
        )

    @patch.object(utils, "get_current_datetime")
    def test_future_published_date(self, fake_get_current_datetime):
        "test for a published date in the future"
        fake_get_current_datetime.return_value = self.past_date
        result = docmap_provider.check_published_date(self.future_date_string)
        self.assertEqual(result, True)

    @patch.object(utils, "get_current_datetime")
    def test_old_published_date(self, fake_get_current_datetime):
        "test for a published date in the past"
        fake_get_current_datetime.return_value = self.future_date
        result = docmap_provider.check_published_date(self.past_date_string)
        self.assertEqual(result, False)

    @patch.object(utils, "get_current_datetime")
    def test_near_published_date(self, fake_get_current_datetime):
        "test for a published date that is just slightly in the past"
        fake_get_current_datetime.return_value = self.future_date + datetime.timedelta(
            hours=0
        )
        result = docmap_provider.check_published_date(self.future_date_string)
        self.assertEqual(result, True)

    def test_none(self):
        "test for a non-date string value"
        result = docmap_provider.check_published_date(None)
        self.assertEqual(result, True)


class TestInputComputerFileUrlFromSteps(unittest.TestCase):
    "tests for input_computer_file_url_from_steps()"

    def setUp(self):
        self.caller_name = "test"
        self.version_doi = "10.7554/eLife.95901.1"
        self.logger = FakeLogger()

    def test_input_computer_file_url_from_steps(self):
        "test simple docmap steps data returning a MECA computer-file URL"
        meca_url = "s3://example/example.meca"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [{"type": "computer-file", "url": meca_url}],
                    }
                ]
            }
        ]
        result = docmap_provider.input_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, meca_url)

    def test_url_missing(self):
        "test no computer-file URL data"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [{"type": "computer-file"}],
                    }
                ]
            }
        ]
        expected = None
        result = docmap_provider.input_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, expected)

    def test_content_missing(self):
        "test no content data present"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                    }
                ]
            }
        ]
        expected = None
        result = docmap_provider.input_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, expected)

    def test_exception(self):
        "test raising exception"
        steps = None
        with self.assertRaises(TypeError):
            docmap_provider.input_computer_file_url_from_steps(
                steps, self.version_doi, self.caller_name, self.logger
            )


class TestOutputComputerFileUrlFromSteps(unittest.TestCase):
    "tests for output_computer_file_url_from_steps()"

    def setUp(self):
        self.caller_name = "test"
        self.version_doi = "10.7554/eLife.95901.1"
        self.logger = FakeLogger()

    def test_output_computer_file_url_from_steps(self):
        "test simple docmap steps data returning a MECA computer-file URL"
        meca_url = "s3://example/reviewed-preprints/example.meca"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [
                            {
                                "type": "computer-file",
                                "url": "s3://example/example.meca",
                            }
                        ],
                    }
                ]
            },
            {
                "actions": [
                    {
                        "outputs": [
                            {
                                "type": "preprint",
                                "identifier": "95901",
                                "doi": "10.7554/eLife.95901.1",
                                "versionIdentifier": "1",
                                "license": "http://creativecommons.org/licenses/by/4.0/",
                                "content": [
                                    {
                                        "type": "computer-file",
                                        "url": meca_url,
                                    }
                                ],
                            }
                        ]
                    }
                ]
            },
        ]
        result = docmap_provider.output_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, meca_url)

    def test_url_missing(self):
        "test no computer-file URL data"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [
                            {
                                "type": "computer-file",
                                "url": "s3://example/example.meca",
                            }
                        ],
                    }
                ]
            },
            {
                "actions": [
                    {
                        "outputs": [
                            {
                                "type": "preprint",
                                "identifier": "95901",
                                "doi": "10.7554/eLife.95901.1",
                                "versionIdentifier": "1",
                                "license": "http://creativecommons.org/licenses/by/4.0/",
                                "content": [{"type": "computer-file"}],
                            }
                        ]
                    }
                ]
            },
        ]
        expected = None
        result = docmap_provider.output_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, expected)

    def test_content_missing(self):
        "test no output content step"
        steps = [
            {
                "inputs": [
                    {
                        "type": "preprint",
                        "content": [
                            {
                                "type": "computer-file",
                                "url": "s3://example/example.meca",
                            }
                        ],
                    }
                ]
            },
        ]
        expected = None
        result = docmap_provider.output_computer_file_url_from_steps(
            steps, self.version_doi, self.caller_name, self.logger
        )
        self.assertEqual(result, expected)

    def test_exception(self):
        "test raising exception"
        steps = None
        with self.assertRaises(TypeError):
            docmap_provider.output_computer_file_url_from_steps(
                steps, self.version_doi, self.caller_name, self.logger
            )
