import unittest
from ddt import ddt, data, unpack
from mock import patch
from activity.activity_DepositAssets import activity_DepositAssets
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeStorageContext, FakeSession, FakeLogger
import tests.activity.test_activity_data as test_activity_data


activity_data = {
    "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
    "article_id": "353",
    "result": "ingested",
    "status": "vor",
    "version": "1",
    "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
    "requested_action": "ingest",
    "message": None,
    "update_date": "2012-12-13T00:00:00Z",
}


@ddt
class TestDepositAssets(unittest.TestCase):
    def setUp(self):
        self.depositassets = activity_DepositAssets(
            settings_mock, None, None, None, None
        )
        self.depositassets.logger = FakeLogger()

    @unpack
    @data(
        {"input": ".tif", "expected": [".tif"]},
        {"input": ".jpg, .tiff, .png", "expected": [".jpg", ".tiff", ".png"]},
    )
    def test_get_no_download_extensions(self, input, expected):
        result = self.depositassets.get_no_download_extensions(input)
        self.assertListEqual(result, expected)

    @unpack
    @data(
        (None, None),
        ("image.jpg", "image/jpeg"),
        ("/folder/file.test.pdf", "application/pdf"),
        ("/folder/weird_file.wdl", "binary/octet-stream"),
        ("a_file", "binary/octet-stream"),
    )
    def test_content_type_from_file_name(self, input, expected):
        result = self.depositassets.content_type_from_file_name(input)
        self.assertEqual(result, expected)

    @patch("activity.activity_DepositAssets.get_session")
    @patch("activity.activity_DepositAssets.storage_context")
    @patch.object(activity_DepositAssets, "emit_monitor_event")
    def test_activity_success(self, fake_emit, fake_storage_context, fake_session):

        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)

        result = self.depositassets.do_activity(activity_data)

        self.assertEqual(self.depositassets.ACTIVITY_SUCCESS, result)

    @patch("activity.activity_DepositAssets.get_session")
    @patch("activity.activity_DepositAssets.storage_context")
    @patch.object(activity_DepositAssets, "emit_monitor_event")
    def test_activity_permanent_failure(
        self, fake_emit, fake_storage_context, fake_session
    ):

        fake_storage_context.side_effect = Exception("An error occurred")
        fake_session.return_value = FakeSession(test_activity_data.session_example)

        result = self.depositassets.do_activity(activity_data)

        self.assertEqual(self.depositassets.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == "__main__":
    unittest.main()
