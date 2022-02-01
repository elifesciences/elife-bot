import unittest
from collections import OrderedDict
from mock import patch
from starter.starter_PostPerfectPublication import starter_PostPerfectPublication
from starter.starter_helper import NullRequiredDataException
import tests.settings_mock as settings_mock
import tests.test_data as test_data
from tests.classes_mock import FakeSWFClient
from tests.activity.classes_mock import FakeLogger


class TestStarterPostPerfectPublication(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.starter = starter_PostPerfectPublication(settings_mock, self.logger)

    def test_get_workflow_params(self):
        expected = OrderedDict(
            [
                ("domain", ""),
                ("task_list", ""),
                ("workflow_id", "PostPerfectPublication_353.1.lax"),
                ("workflow_name", "PostPerfectPublication"),
                ("workflow_version", "1"),
                ("child_policy", None),
                ("execution_start_to_close_timeout", None),
                (
                    "input",
                    (
                        "{"
                        '"run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",'
                        ' "article_id": "353",'
                        ' "result": "error",'
                        ' "status": "vor",'
                        ' "version": "1",'
                        ' "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",'
                        ' "requested_action": "publish",'
                        ' "message": "An error abc has occurred",'
                        ' "update_date": "2012-12-13T00:00:00Z"'
                        "}"
                    ),
                ),
            ]
        )
        params = self.starter.get_workflow_params(test_data.data_error_lax)
        self.assertEqual(params, expected)

    def test_post_perfect_publication_starter_no_article(self):
        self.assertRaises(
            NullRequiredDataException,
            self.starter.start,
            settings=settings_mock,
            info=test_data.data_invalid_lax,
        )

    @patch("boto3.client")
    def test_post_perfect_publication_starter(self, fake_client):
        fake_client.return_value = FakeSWFClient()
        self.starter.start(info=test_data.data_error_lax, settings=settings_mock)
