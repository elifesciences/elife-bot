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
        self.applyversionnumber = activity_ApplyVersionNumber(
            settings_mock, FakeLogger(), None, None, None
        )

    def tearDown(self):
        TempDirectory.cleanup_all()

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


class TestFindXmlFilenameInMap(unittest.TestCase):
    def test_find_xml_filename_in_map(self):
        new_name = activity_module.find_xml_filename_in_map(example_file_name_map)
        self.assertEqual(new_name, "elife-15224-v1.xml")
