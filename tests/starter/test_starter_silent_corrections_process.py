import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_SilentCorrectionsProcess import starter_SilentCorrectionsProcess
from starter.starter_helper import NullRequiredDataException
from tests.classes_mock import FakeLayer1
from tests.activity.classes_mock import FakeLogger
import tests.settings_mock as settings_mock
import tests.test_data as test_data


class TestStarterSilentCorrectionsProcess(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_SilentCorrectionsProcess(settings_mock, self.logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "SilentCorrectionsProcess_00353.1"),
                ("workflow_name", "SilentCorrectionsProcess"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                (
                    "input",
                    (
                        "{"
                        '"run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",'
                        ' "article_id": "00353",'
                        ' "result": "ingested",'
                        ' "status": "vor",'
                        ' "version": "1",'
                        ' "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",'
                        ' "requested_action": "ingest",'
                        ' "force": false,'
                        ' "message": null,'
                        ' "update_date": "2012-12-13T00:00:00Z",'
                        ' "run_type": null'
                        "}"
                    ),
                ),
            ]
        )
        params = self.starter.get_workflow_params(test_data.data_ingested_lax)
        self.assertEqual(params, expected)

    def test_process_article_zip_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            **test_data.data_invalid_lax
        )

    @patch("boto.swf.layer1.Layer1")
    def test_process_article_zip_starter(self, fake_boto_conn):
        fake_boto_conn.return_value = FakeLayer1()
        self.starter.start(settings=settings_mock, **test_data.data_ingested_lax)
