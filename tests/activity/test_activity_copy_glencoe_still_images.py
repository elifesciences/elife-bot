import unittest
import settings_mock
from activity.activity_CopyGlencoeStillImages import activity_CopyGlencoeStillImages
from mock import patch, MagicMock
from classes_mock import FakeSession
from classes_mock import FakeStorageContext
import test_activity_data as test_activity_data
import provider.glencoe_check as glencoe_check

class TestCopyGlencoeStillImages(unittest.TestCase):

    def setUp(self):
        self.copyglencoestillimages = activity_CopyGlencoeStillImages(settings_mock, None, None, None, None)

    @patch.object(activity_CopyGlencoeStillImages, 'store_file')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata, fake_store_file):
        # Given
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.return_value = test_activity_data.glencoe_metadata
        self.copyglencoestillimages.logger = MagicMock()

        # When
        result = self.copyglencoestillimages.do_activity(test_activity_data.data_example_before_publish)

        # Then
        self.assertEqual(result, self.copyglencoestillimages.ACTIVITY_SUCCESS)

    @patch.object(activity_CopyGlencoeStillImages, 'store_file')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity_error(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata, fake_store_file):
        # Given
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.return_value = test_activity_data.glencoe_metadata
        self.copyglencoestillimages.logger = MagicMock()
        fake_store_file.side_effect = Exception("Something went wrong!")

        # When
        result = self.copyglencoestillimages.do_activity(test_activity_data.data_example_before_publish)

        # Then
        self.assertEqual(result, self.copyglencoestillimages.ACTIVITY_PERMANENT_FAILURE)

    def test_validate_cdn(self):
        # Given
        files_in_cdn = test_activity_data.cdn_folder_files_article_07398

        # When
        res_do_videos_match_jpgs, res_files_in_cdn, res_videos = self.copyglencoestillimages.validate_cdn(files_in_cdn)

        # Then
        self.assertEqual(res_files_in_cdn, files_in_cdn)
        self.assertEqual(res_videos, test_activity_data.cdn_folder_videos_article_07398)
        self.assertEqual(res_do_videos_match_jpgs, True)



if __name__ == '__main__':
    unittest.main()
