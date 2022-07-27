import os
import shutil
import unittest
from mock import patch
from testfixtures import TempDirectory
from ddt import ddt, data, unpack
from activity import activity_ApplyVersionNumber as activity_module
from activity.activity_ApplyVersionNumber import activity_ApplyVersionNumber
from tests.activity import settings_mock
from tests.activity.classes_mock import FakeLogger, FakeSession, FakeStorageContext
import tests.activity.test_activity_data as test_data


example_key_names = [
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures.pdf",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.pdf",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.xml",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1-code1.wrl",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media.mp4",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1.mov",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-media1.avi",
]

example_file_name_map = {
    "elife-15224-fig2-figsupp1.tif": "elife-15224-fig2-figsupp1-v1.tif",
    "elife-15224-fig3.tif": "elife-15224-fig3-v1.tif",
    "elife-15224-fig4.tif": "elife-15224-fig4-v1.tif",
    "elife-15224.xml": "elife-15224-v1.xml",
    "elife-15224-resp-fig2.tif": "elife-15224-resp-fig2-v1.tif",
    "elife-15224-fig4-figsupp1.tif": "elife-15224-fig4-figsupp1-v1.tif",
    "elife-15224-resp-fig3.tif": "elife-15224-resp-fig3-v1.tif",
    "elife-15224-figures.pdf": "elife-15224-figures-v1.pdf",
    "elife-15224-resp-fig1.tif": "elife-15224-resp-fig1-v1.tif",
    "elife-15224-fig5-figsupp1.tif": "elife-15224-fig5-figsupp1-v1.tif",
    "elife-15224.pdf": "elife-15224-v1.pdf",
    "elife-15224-fig1-figsupp2.tif": "elife-15224-fig1-figsupp2-v1.tif",
    "elife-15224-fig1-figsupp1.tif": "elife-15224-fig1-figsupp1-v1.tif",
    "elife-15224-fig3-figsupp1.tif": "elife-15224-fig3-figsupp1-v1.tif",
    "elife-15224-fig1.tif": "elife-15224-fig1-v1.tif",
    "elife-15224-fig2.tif": "elife-15224-fig2-v1.tif",
    "elife-15224-fig2-figsupp2.tif": "elife-15224-fig2-figsupp2-v1.tif",
    "elife-15224-fig5.tif": "elife-15224-fig5-v1.tif",
    "elife-15224-media1-code1.wrl": "elife-15224-media1-code1-v1.wrl",
    "elife-15224-media.mp4": "elife-15224-media.mp4",
    "elife-15224-media1.mov": "elife-15224-media1.mov",
    "elife-15224-resp-media1.avi": "elife-15224-resp-media1.avi",
}

example_key_names_with_version = [
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures-v1.pdf",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3-v1.tif",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-v1.pdf",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-v1.xml",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1-code1-v1.wrl",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media.mp4",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1.mov",
    "15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-media1.avi",
]

example_file_name_map_with_version = {
    "elife-15224-fig1-figsupp1-v1.tif": "elife-15224-fig1-figsupp1-v2.tif",
    "elife-15224-fig2-figsupp1-v1.tif": "elife-15224-fig2-figsupp1-v2.tif",
    "elife-15224-fig3-v1.tif": "elife-15224-fig3-v2.tif",
    "elife-15224-fig4-v1.tif": "elife-15224-fig4-v2.tif",
    "elife-15224-resp-fig2-v1.tif": "elife-15224-resp-fig2-v2.tif",
    "elife-15224-fig4-figsupp1-v1.tif": "elife-15224-fig4-figsupp1-v2.tif",
    "elife-15224-resp-fig3-v1.tif": "elife-15224-resp-fig3-v2.tif",
    "elife-15224-figures-v1.pdf": "elife-15224-figures-v2.pdf",
    "elife-15224-resp-fig1-v1.tif": "elife-15224-resp-fig1-v2.tif",
    "elife-15224-fig5-figsupp1-v1.tif": "elife-15224-fig5-figsupp1-v2.tif",
    "elife-15224-v1.pdf": "elife-15224-v2.pdf",
    "elife-15224-fig1-figsupp2-v1.tif": "elife-15224-fig1-figsupp2-v2.tif",
    "elife-15224-fig3-figsupp1-v1.tif": "elife-15224-fig3-figsupp1-v2.tif",
    "elife-15224-fig1-v1.tif": "elife-15224-fig1-v2.tif",
    "elife-15224-fig2-v1.tif": "elife-15224-fig2-v2.tif",
    "elife-15224-fig2-figsupp2-v1.tif": "elife-15224-fig2-figsupp2-v2.tif",
    "elife-15224-fig5-v1.tif": "elife-15224-fig5-v2.tif",
    "elife-15224-v1.xml": "elife-15224-v2.xml",
    "elife-15224-media1-code1-v1.wrl": "elife-15224-media1-code1-v2.wrl",
    "elife-15224-media.mp4": "elife-15224-media.mp4",
    "elife-15224-media1.mov": "elife-15224-media1.mov",
    "elife-15224-resp-media1.avi": "elife-15224-resp-media1.avi",
}


@ddt
class TestApplyVersionNumber(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.applyversionnumber = activity_ApplyVersionNumber(
            settings_mock, self.logger, None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        self.applyversionnumber.clean_tmp_dir()

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_ApplyVersionNumber, "emit_monitor_event")
    @patch("activity.activity_ApplyVersionNumber.get_session")
    def test_do_activity(
        self, mock_session, fake_emit_monitor_event, fake_storage_context
    ):
        directory = TempDirectory()
        # mocks
        mock_session.return_value = FakeSession(test_data.session_example)
        fake_emit_monitor_event.return_value = True
        fake_storage_context.return_value = FakeStorageContext(
            dest_folder=directory.path
        )
        activity_data = test_data.ApplyVersionNumber_data_no_renaming
        # do_activity
        result = self.applyversionnumber.do_activity(activity_data)
        # assertions
        self.assertEqual(result, self.applyversionnumber.ACTIVITY_SUCCESS)

    @patch.object(activity_ApplyVersionNumber, "emit_monitor_event")
    @patch("activity.activity_ApplyVersionNumber.get_session")
    @data(test_data.session_example)
    def test_do_activity_no_version_error(
        self, session_example, mock_session, fake_emit_monitor_event
    ):
        # given
        fake_emit_monitor_event.return_value = True
        session_example = session_example.copy()
        del session_example["version"]
        mock_session.return_value = FakeSession(session_example)
        activity_data = test_data.ApplyVersionNumber_data_no_renaming

        # when
        result = self.applyversionnumber.do_activity(activity_data)

        # then
        fake_emit_monitor_event.assert_called_with(
            settings_mock,
            session_example["article_id"],
            None,
            activity_data["run"],
            self.applyversionnumber.pretty_name,
            "error",
            "Error in applying version number to files for "
            + session_example["article_id"]
            + " message: No version available",
        )
        self.assertEqual(result, self.applyversionnumber.ACTIVITY_PERMANENT_FAILURE)

    @patch.object(activity_ApplyVersionNumber, "emit_monitor_event")
    @patch("activity.activity_ApplyVersionNumber.get_session")
    def test_do_activity_session_exception(self, mock_session, fake_emit_monitor_event):
        # given
        fake_emit_monitor_event.return_value = True
        activity_data = test_data.ApplyVersionNumber_data_no_renaming
        exception_message = "An exception"
        mock_session.side_effect = Exception(exception_message)

        # when
        result = self.applyversionnumber.do_activity(activity_data)

        # then
        self.assertEqual(result, self.applyversionnumber.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(self.logger.logexception, exception_message)

    @patch.object(activity_ApplyVersionNumber, "emit_monitor_event")
    @patch("activity.activity_ApplyVersionNumber.get_session")
    @patch.object(activity_ApplyVersionNumber, "rename_article_s3_objects")
    def test_do_activity_rename_exception(
        self, fake_rename, mock_session, fake_emit_monitor_event
    ):
        # given
        fake_emit_monitor_event.return_value = True
        mock_session.return_value = FakeSession(test_data.session_example)
        activity_data = test_data.ApplyVersionNumber_data_no_renaming
        exception_message = "An exception"
        fake_rename.side_effect = Exception(exception_message)

        # when
        result = self.applyversionnumber.do_activity(activity_data)

        # then
        self.assertEqual(result, self.applyversionnumber.ACTIVITY_PERMANENT_FAILURE)
        self.assertEqual(self.logger.logexception, exception_message)


@ddt
class TestNewFilename(unittest.TestCase):
    @unpack
    @data(
        {"file": "elife-15224.xml", "version": "1", "expected": "elife-15224-v1.xml"},
        {
            "file": "elife-code1.tar.gz",
            "version": "1",
            "expected": "elife-code1-v1.tar.gz",
        },
        {
            "file": "elife-15224-v1.xml",
            "version": "1",
            "expected": "elife-15224-v1.xml",
        },
        {
            "file": "elife-15224-v1.xml",
            "version": "2",
            "expected": "elife-15224-v2.xml",
        },
        {
            "file": "elife-code1-v1.tar.gz",
            "version": "2",
            "expected": "elife-code1-v2.tar.gz",
        },
    )
    def test_new_filename(self, file, version, expected):
        result = activity_module.new_filename(file, version)
        self.assertEqual(result, expected)


class TestRenameS3Objects(unittest.TestCase):
    def setUp(self):
        self.activity = activity_ApplyVersionNumber(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(activity_module, "storage_context")
    def test_rename_s3_objects(self, fake_storage_context):
        "test with S3 object names not containing version numbers"
        directory = TempDirectory()
        # copy renamed files to the temp directory
        for key_name in test_data.key_names:
            new_name = os.path.join(directory.path, key_name.replace("-v1", ""))
            os.makedirs(os.path.dirname(new_name), exist_ok=True)
            shutil.copy(
                os.path.join(test_data.ExpandArticle_files_source_folder, key_name),
                new_name,
            )
        # mocks
        fake_storage_context.return_value = FakeStorageContext(
            directory=directory.path, dest_folder=directory.path
        )
        # test data
        bucket_name = (
            settings_mock.publishing_buckets_prefix + settings_mock.expanded_bucket
        )
        bucket_folder_name = test_data.session_example.get("expanded_folder")
        file_name_map = {"elife-00353-fig1.tif": "elife-00353-fig1-v99.tif"}
        # invoke the function
        self.activity.rename_s3_objects(bucket_name, bucket_folder_name, file_name_map)
        # assertions
        expanded_folder_list = os.listdir(
            os.path.join(directory.path, bucket_folder_name)
        )
        self.assertTrue("elife-00353-fig1-v99.tif" in expanded_folder_list)


class TestBuildFileNameMap(unittest.TestCase):
    def test_build_file_name_map(self):
        new_map = activity_module.build_file_name_map(
            example_key_names, 1, FakeLogger()
        )
        self.assertDictEqual(new_map, example_file_name_map)

    @patch.object(activity_module, "new_filename")
    def test_build_file_name_map_no_renamed(self, fake_new_filename):
        "test if there is no renamed file for a file"
        logger = FakeLogger()
        fake_new_filename.return_value = None
        activity_module.build_file_name_map(example_key_names, 1, logger)
        self.assertEqual(
            logger.loginfo[-1],
            "there is no renamed file for elife-15224-media1-code1.wrl",
        )


class TestFindXmlFilenameInMap(unittest.TestCase):
    def test_find_xml_filename_in_map(self):
        new_name = activity_module.find_xml_filename_in_map(example_file_name_map)
        self.assertEqual(new_name, "elife-15224-v1.xml")

    def test_find_xml_filename_in_map_empty(self):
        new_name = activity_module.find_xml_filename_in_map({})
        self.assertIsNone(new_name)
