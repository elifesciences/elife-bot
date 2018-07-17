import unittest
from activity.activity_ConvertImagesToJPG import activity_ConvertImagesToJPG
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeStorageContext, FakeSession
from tests.activity import test_activity_data
from mock import patch


class TestConvertImagesToJPG(unittest.TestCase):
    def setUp(self):
        self.convertimagestojpg = activity_ConvertImagesToJPG(settings_mock, None, None, None, None)
        self.convertimagestojpg.logger = FakeLogger()

    @patch('provider.image_conversion.generate_images')
    @patch('activity.activity_ConvertImagesToJPG.get_session')
    @patch('activity.activity_ConvertImagesToJPG.storage_context')
    @patch.object(activity_ConvertImagesToJPG, 'emit_monitor_event')
    def test_activity_success(self, fake_emit, fake_storage_context, fake_session, fake_gen_images):

        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        activity_data = test_activity_data.data_example_before_publish

        result = self.convertimagestojpg.do_activity(activity_data)

        self.assertEqual(self.convertimagestojpg.ACTIVITY_SUCCESS, result)


    @patch('activity.activity_ConvertImagesToJPG.get_session')
    @patch('activity.activity_ConvertImagesToJPG.storage_context')
    @patch.object(activity_ConvertImagesToJPG, 'emit_monitor_event')
    def test_activity_failure(self, fake_emit, fake_storage_context, fake_session):

        fake_storage_context.side_effect = Exception("An error occurred")
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        activity_data = test_activity_data.data_example_before_publish

        result = self.convertimagestojpg.do_activity(activity_data)

        self.assertEqual(self.convertimagestojpg.ACTIVITY_PERMANENT_FAILURE, result)


if __name__ == '__main__':
    unittest.main()
