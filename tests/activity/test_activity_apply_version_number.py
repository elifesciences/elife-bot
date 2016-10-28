import unittest
from ddt import ddt, data, unpack
import settings_mock
from activity.activity_ApplyVersionNumber import activity_ApplyVersionNumber
from mock import mock, patch
import test_activity_data as test_data
from classes_mock import FakeSession
import shutil
import helpers

example_file_name_map = {u'elife-15224-fig2-figsupp1.tif': u'elife-15224-fig2-figsupp1-v1.tif', u'elife-15224-fig3.tif': u'elife-15224-fig3-v1.tif', u'elife-15224-fig4.tif': u'elife-15224-fig4-v1.tif', u'elife-15224.xml': u'elife-15224-v1.xml', u'elife-15224-resp-fig2.tif': u'elife-15224-resp-fig2-v1.tif', u'elife-15224-fig4-figsupp1.tif': u'elife-15224-fig4-figsupp1-v1.tif', u'elife-15224-resp-fig3.tif': u'elife-15224-resp-fig3-v1.tif', u'elife-15224-figures.pdf': u'elife-15224-figures-v1.pdf', u'elife-15224-resp-fig1.tif': u'elife-15224-resp-fig1-v1.tif', u'elife-15224-fig5-figsupp1.tif': u'elife-15224-fig5-figsupp1-v1.tif', u'elife-15224.pdf': u'elife-15224-v1.pdf', u'elife-15224-fig1-figsupp2.tif': u'elife-15224-fig1-figsupp2-v1.tif', u'elife-15224-fig1-figsupp1.tif': u'elife-15224-fig1-figsupp1-v1.tif', u'elife-15224-fig3-figsupp1.tif': u'elife-15224-fig3-figsupp1-v1.tif', u'elife-15224-fig1.tif': u'elife-15224-fig1-v1.tif', u'elife-15224-fig2.tif': u'elife-15224-fig2-v1.tif', u'elife-15224-fig2-figsupp2.tif': u'elife-15224-fig2-figsupp2-v1.tif', u'elife-15224-fig5.tif': u'elife-15224-fig5-v1.tif'}
example_key_names = [u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures.pdf', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.pdf', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.xml']

example_key_names_some_with_version = [u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1-v1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures.pdf',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3-v2.tif',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.pdf',
                                       u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-v1.xml']

example_file_name_map_some_with_version = {u'elife-15224-fig1-figsupp1-v1.tif': u'elife-15224-fig1-figsupp1-v1.tif',
                                           u'elife-15224-fig2-figsupp1.tif': u'elife-15224-fig2-figsupp1-v1.tif',
                                           u'elife-15224-fig3.tif': u'elife-15224-fig3-v1.tif',
                                           u'elife-15224-fig4.tif': u'elife-15224-fig4-v1.tif',
                                           u'elife-15224-resp-fig2.tif': u'elife-15224-resp-fig2-v1.tif',
                                           u'elife-15224-fig4-figsupp1.tif': u'elife-15224-fig4-figsupp1-v1.tif',
                                           u'elife-15224-resp-fig3-v2.tif': u'elife-15224-resp-fig3-v1.tif',
                                           u'elife-15224-figures.pdf': u'elife-15224-figures-v1.pdf',
                                           u'elife-15224-resp-fig1.tif': u'elife-15224-resp-fig1-v1.tif',
                                           u'elife-15224-fig5-figsupp1.tif': u'elife-15224-fig5-figsupp1-v1.tif',
                                           u'elife-15224.pdf': u'elife-15224-v1.pdf',
                                           u'elife-15224-fig1-figsupp2.tif': u'elife-15224-fig1-figsupp2-v1.tif',
                                           u'elife-15224-fig3-figsupp1.tif': u'elife-15224-fig3-figsupp1-v1.tif',
                                           u'elife-15224-fig1.tif': u'elife-15224-fig1-v1.tif',
                                           u'elife-15224-fig2.tif': u'elife-15224-fig2-v1.tif',
                                           u'elife-15224-fig2-figsupp2.tif': u'elife-15224-fig2-figsupp2-v1.tif',
                                           u'elife-15224-fig5.tif': u'elife-15224-fig5-v1.tif',
                                           u'elife-15224-v1.xml': u'elife-15224-v1.xml'}

@ddt
class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.applyversionnumber = activity_ApplyVersionNumber(settings_mock, None, None, None, None)

    @patch.object(activity_ApplyVersionNumber, 'emit_monitor_event')
    @patch('activity.activity_ApplyVersionNumber.Session')
    @data(test_data.session_example)
    def test_do_activity_no_version_error(self, session_example, mock_session, fake_emit_monitor_event):
        #given
        session_example = session_example.copy()
        del session_example['version']
        mock_session.return_value = FakeSession(session_example)
        data = test_data.ApplyVersionNumber_data_no_renaming

        #when
        result = self.applyversionnumber.do_activity(data)

        #then
        fake_emit_monitor_event.assert_called_with(settings_mock, session_example['article_id'], None, data['run'],
                                                   self.applyversionnumber.pretty_name, "error",
                                                   "Error in applying version number to files for " +
                                                   session_example['article_id'] +
                                                   " message: No version available")
        self.assertEqual(result, self.applyversionnumber.ACTIVITY_PERMANENT_FAILURE)

    def test_find_xml_filename_in_map(self):
        new_name = self.applyversionnumber.find_xml_filename_in_map(example_file_name_map)
        self.assertEqual(new_name, u'elife-15224-v1.xml')

    @unpack
    @data({'key_names': example_key_names, 'version': '1', 'expected': example_file_name_map},
          {'key_names': example_key_names_some_with_version, 'version': '1', 'expected': example_file_name_map_some_with_version})
    def test_build_file_name_map(self, key_names, version, expected):
        result = self.applyversionnumber.build_file_name_map(key_names, version)
        self.assertDictEqual(result, expected)

    @unpack
    @data({'file': u'elife-15224.xml', 'version': '1', 'expected': u'elife-15224-v1.xml'},
          {'file': u'elife-15224-v1.xml', 'version': '1', 'expected': u'elife-15224-v1.xml'},
          {'file': u'elife-15224-v1.xml', 'version': '2', 'expected': u'elife-15224-v2.xml'})
    def test_new_filename(self, file, version, expected):
        result = self.applyversionnumber.new_filename(file, version)
        self.assertEqual(result, expected)

    @data(u'elife-15224-fig1-figsupp1.tif')
    def test_file_parts(self, filename):
        prefix, extension = self.applyversionnumber.file_parts(filename)
        self.assertEqual(prefix, u'elife-15224-fig1-figsupp1')
        self.assertEqual(extension, u'tif')

    @data(u'elife-15224-fig1-figsupp1.tif', u'elife-15224-resp-fig1.tif', u'elife-15224-figures.pdf', u'elife-15802-fig9-data3.docx', u'elife-11792.mp4')
    def test_is_video_file_false(self, filename):
        result = self.applyversionnumber.is_video_file(filename)
        self.assertFalse(result)

    @data(u'elife-11792-media2.mp4', u'elife-15224-fig1-figsupp1-media.tif')
    def test_is_video_file_true(self,filename):
        result = self.applyversionnumber.is_video_file(filename)
        self.assertTrue(result)

    @patch('activity.activity_ApplyVersionNumber.path.join')
    def test_rewrite_xml_file(self, mock_path_join):
        #given
        helpers.create_folder('tests/files_dest_ApplyVersionNumber')
        shutil.copy(u'tests/files_source/ApplyVersionNumber/elife-15224-v1.xml', u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml')
        mock_path_join.return_value = u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml'

        #when
        self.applyversionnumber.rewrite_xml_file(u'elife-15224-v1.xml', example_file_name_map)

        #then
        with open(u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml', 'r') as result_file:
            result_file_content = result_file.read()
        with open(u'tests/files_source/ApplyVersionNumber/elife-15224-v1-rewritten.xml', 'r') as expected_file:
            expected_file_content = expected_file.read()
        self.assertEqual(result_file_content, expected_file_content)

        helpers.delete_folder('tests/files_dest_ApplyVersionNumber', True)

    @patch('activity.activity_ApplyVersionNumber.path.join')
    def test_rewrite_xml_file_no_changes(self, mock_path_join):
        #given
        helpers.create_folder('tests/files_dest_ApplyVersionNumber')
        shutil.copy(u'tests/files_source/ApplyVersionNumber/elife-15224-v1-rewritten.xml', u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml')
        mock_path_join.return_value = u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml'

        #when
        self.applyversionnumber.rewrite_xml_file(u'elife-15224-v1.xml', example_file_name_map)

        #then
        with open(u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml', 'r') as result_file:
            result_file_content = result_file.read()
        with open(u'tests/files_source/ApplyVersionNumber/elife-15224-v1-rewritten.xml', 'r') as expected_file:
            expected_file_content = expected_file.read()
        self.assertEqual(result_file_content, expected_file_content)

        helpers.delete_folder('tests/files_dest_ApplyVersionNumber', True)

if __name__ == '__main__':
    unittest.main()
