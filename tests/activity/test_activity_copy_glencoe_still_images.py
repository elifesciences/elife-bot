import unittest
import settings_mock
from activity.activity_CopyGlencoeStillImages import activity_CopyGlencoeStillImages
from mock import patch, MagicMock
from classes_mock import FakeSession
from classes_mock import FakeStorageContext
from classes_mock import FakeLogger
import test_activity_data as test_activity_data
import provider.glencoe_check as glencoe_check

class TestCopyGlencoeStillImages(unittest.TestCase):

    def setUp(self):
        self.copyglencoestillimages = activity_CopyGlencoeStillImages(settings_mock, None, None, None, None)

    @patch.object(activity_CopyGlencoeStillImages, 'list_files_from_cdn')
    @patch.object(activity_CopyGlencoeStillImages, 'store_jpgs')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata,
                         fake_store_jpgs, fake_list_files_from_cdn):
        # Given
        activity_data = test_activity_data.data_example_before_publish
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.return_value = test_activity_data.glencoe_metadata
        fake_store_jpgs.return_value = test_activity_data.jpgs_added_in_cdn
        self.copyglencoestillimages.logger = FakeLogger()
        fake_list_files_from_cdn.return_value = test_activity_data.cdn_folder_files + \
                                                test_activity_data.jpgs_added_in_cdn

        # When
        result = self.copyglencoestillimages.do_activity(activity_data)

        # Then
        self.assertEqual(self.copyglencoestillimages.ACTIVITY_SUCCESS, result)

    @patch.object(activity_CopyGlencoeStillImages, 'list_files_from_cdn')
    @patch.object(activity_CopyGlencoeStillImages, 'store_jpgs')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity_success_no_videos_for_article(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata,
                         fake_store_jpgs, fake_list_files_from_cdn):
        # Given
        activity_data = test_activity_data.data_example_before_publish
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.side_effect = AssertionError("article has no videos - url requested: ...")
        self.copyglencoestillimages.logger = FakeLogger()

        # When
        result = self.copyglencoestillimages.do_activity(activity_data)

        # Then
        self.assertEqual(self.copyglencoestillimages.ACTIVITY_SUCCESS, result)

    @patch.object(activity_CopyGlencoeStillImages, 'store_jpgs')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity_error(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata, fake_store_jpgs):
        # Given
        activity_data = test_activity_data.data_example_before_publish
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.return_value = test_activity_data.glencoe_metadata
        self.copyglencoestillimages.logger = MagicMock()
        fake_store_jpgs.side_effect = Exception("Something went wrong!")

        # When
        result = self.copyglencoestillimages.do_activity(activity_data)

        # Then
        self.assertEqual(result, self.copyglencoestillimages.ACTIVITY_PERMANENT_FAILURE)
        fake_emit.assert_called_with(settings_mock,
                                     activity_data["article_id"],
                                     activity_data["version"],
                                     activity_data["run"],
                                     self.copyglencoestillimages.pretty_name,
                                     "error",
                                     "An error occurred when checking/copying Glencoe still images. Article " +
                                     activity_data["article_id"] + "; message: Something went wrong!")


    @patch.object(activity_CopyGlencoeStillImages, 'list_files_from_cdn')
    @patch.object(activity_CopyGlencoeStillImages, 'store_jpgs')
    @patch('provider.glencoe_check.metadata')
    @patch('activity.activity_CopyGlencoeStillImages.StorageContext')
    @patch('activity.activity_CopyGlencoeStillImages.Session')
    @patch.object(activity_CopyGlencoeStillImages, 'emit_monitor_event')
    def test_do_activity_bad_files(self, fake_emit, fake_session, fake_storage_context, fake_glencoe_metadata,
                                   fake_store_jpgs, fake_list_files_from_cdn):
        # Given
        activity_data = test_activity_data.data_example_before_publish
        fake_storage_context.return_value = FakeStorageContext()
        fake_session.return_value = FakeSession(test_activity_data.session_example)
        fake_glencoe_metadata.return_value = test_activity_data.glencoe_metadata
        self.copyglencoestillimages.logger = MagicMock()
        fake_list_files_from_cdn.return_value = test_activity_data.cdn_folder_files
        fake_store_jpgs.return_value = test_activity_data.jpgs_added_in_cdn

        # When
        result = self.copyglencoestillimages.do_activity(activity_data)

        # Then
        self.assertEqual(result, self.copyglencoestillimages.ACTIVITY_PERMANENT_FAILURE)
        fake_emit.assert_called_with(settings_mock,
                                     activity_data["article_id"],
                                     activity_data["version"],
                                     activity_data["run"],
                                     self.copyglencoestillimages.pretty_name,
                                     "error",
                                     "Not all still images .jpg have a video with the same name " +
                                     "missing videos file names: ['elife-12620-media1', 'elife-12620-media2']" +
                                     " Please check them against CDN files.")


    def test_validate_jpgs_against_cdn(self):
        # Given
        files_in_cdn = test_activity_data.cdn_folder_files_article_07398
        jpgs_from_glencoe = test_activity_data.cdn_folder_jpgs_article_07398
        self.copyglencoestillimages.logger = FakeLogger()

        # When
        result_bad_files = self.copyglencoestillimages.validate_jpgs_against_cdn(files_in_cdn, jpgs_from_glencoe,
                                                                                 "07398")

        # Then
        self.assertEqual(0, len(result_bad_files))

    def test_validate_pgs_against_cdn_long_article_ids(self):
        # Given
        files_in_cdn = ["elife-1234500230-media1-v1.wmv", "elife-1234500230-media2-v1.mp4",
                        "elife-1234500230-media1-v1.jpg", "elife-1234500230-media2-v1.jpg",
                        "elife-1234500230-fig1-figsupp1-v2-1084w.jpg"]
        jpgs_from_glencoe = ["elife-1234500230-media1-v1.jpg", "elife-1234500230-media2-v1.jpg"]
        self.copyglencoestillimages.logger = FakeLogger()

        # When
        result_bad_files = self.copyglencoestillimages.validate_jpgs_against_cdn(files_in_cdn, jpgs_from_glencoe,
                                                                                 "00230")

        # Then
        self.assertEqual(0, len(result_bad_files))


    def test_validate_pgs_against_cdn_long_article_ids_one_missing(self):
        # Given
        files_in_cdn = ["elife-1234500230-media1-v1.wmv", "elife-1234500230-media2-v1.mp4",
                        "elife-1234500230-media1-v1.jpg", "elife-1234500230-media2-v1.jpg",
                        "elife-1234500230-fig1-figsupp1-v2-1084w.jpg"]
        jpgs_from_glencoe = ["elife-1234500230-media1-v1.jpg", "elife-1234500230-media2-v1.jpg",
                             "elife-1234500230-media3-v1.jpg"]
        self.copyglencoestillimages.logger = FakeLogger()

        # When
        result_bad_files = self.copyglencoestillimages.validate_jpgs_against_cdn(files_in_cdn, jpgs_from_glencoe,
                                                                                 "00230")

        # Then
        self.assertEqual(1, len(result_bad_files))

    # def test_validate_cdn(self):
    #     # Given
    #     files_in_cdn = test_activity_data.cdn_folder_files_article_07398
    #
    #     # When
    #     res_do_videos_match_jpgs, res_files_in_cdn, res_videos = self.copyglencoestillimages.validate_cdn(files_in_cdn)
    #
    #     # Then
    #     self.assertEqual(res_files_in_cdn, files_in_cdn)
    #     self.assertEqual(res_videos, test_activity_data.cdn_folder_videos_article_07398)
    #     self.assertEqual(res_do_videos_match_jpgs, True)




if __name__ == '__main__':
    unittest.main()
