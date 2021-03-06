import unittest
import shutil
from mock import patch
from ddt import ddt, data, unpack
from activity.activity_ApplyVersionNumber import activity_ApplyVersionNumber
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeSession
import tests.activity.test_activity_data as test_data
import tests.activity.helpers as helpers

example_key_names = [u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1.tif',
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
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3.tif',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.pdf',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.xml',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1-code1.wrl',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media.mp4',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1.mov',
                     u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-media1.avi']

example_file_name_map = {u'elife-15224-fig2-figsupp1.tif': u'elife-15224-fig2-figsupp1-v1.tif',
                         u'elife-15224-fig3.tif': u'elife-15224-fig3-v1.tif',
                         u'elife-15224-fig4.tif': u'elife-15224-fig4-v1.tif',
                         u'elife-15224.xml': u'elife-15224-v1.xml',
                         u'elife-15224-resp-fig2.tif': u'elife-15224-resp-fig2-v1.tif',
                         u'elife-15224-fig4-figsupp1.tif': u'elife-15224-fig4-figsupp1-v1.tif',
                         u'elife-15224-resp-fig3.tif': u'elife-15224-resp-fig3-v1.tif',
                         u'elife-15224-figures.pdf': u'elife-15224-figures-v1.pdf',
                         u'elife-15224-resp-fig1.tif': u'elife-15224-resp-fig1-v1.tif',
                         u'elife-15224-fig5-figsupp1.tif': u'elife-15224-fig5-figsupp1-v1.tif',
                         u'elife-15224.pdf': u'elife-15224-v1.pdf',
                         u'elife-15224-fig1-figsupp2.tif': u'elife-15224-fig1-figsupp2-v1.tif',
                         u'elife-15224-fig1-figsupp1.tif': u'elife-15224-fig1-figsupp1-v1.tif',
                         u'elife-15224-fig3-figsupp1.tif': u'elife-15224-fig3-figsupp1-v1.tif',
                         u'elife-15224-fig1.tif': u'elife-15224-fig1-v1.tif',
                         u'elife-15224-fig2.tif': u'elife-15224-fig2-v1.tif',
                         u'elife-15224-fig2-figsupp2.tif': u'elife-15224-fig2-figsupp2-v1.tif',
                         u'elife-15224-fig5.tif': u'elife-15224-fig5-v1.tif',
                         u'elife-15224-media1-code1.wrl': u'elife-15224-media1-code1-v1.wrl',
                         u'elife-15224-media.mp4': u'elife-15224-media.mp4',
                         u'elife-15224-media1.mov': u'elife-15224-media1.mov',
                         u'elife-15224-resp-media1.avi': u'elife-15224-resp-media1.avi'}

example_key_names_with_version = [u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures-v1.pdf',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3-v1.tif',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-v1.pdf',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-v1.xml',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1-code1-v1.wrl',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media.mp4',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-media1.mov',
                                  u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-media1.avi']

example_file_name_map_with_version = {u'elife-15224-fig1-figsupp1-v1.tif': u'elife-15224-fig1-figsupp1-v2.tif',
                                      u'elife-15224-fig2-figsupp1-v1.tif': u'elife-15224-fig2-figsupp1-v2.tif',
                                      u'elife-15224-fig3-v1.tif': u'elife-15224-fig3-v2.tif',
                                      u'elife-15224-fig4-v1.tif': u'elife-15224-fig4-v2.tif',
                                      u'elife-15224-resp-fig2-v1.tif': u'elife-15224-resp-fig2-v2.tif',
                                      u'elife-15224-fig4-figsupp1-v1.tif': u'elife-15224-fig4-figsupp1-v2.tif',
                                      u'elife-15224-resp-fig3-v1.tif': u'elife-15224-resp-fig3-v2.tif',
                                      u'elife-15224-figures-v1.pdf': u'elife-15224-figures-v2.pdf',
                                      u'elife-15224-resp-fig1-v1.tif': u'elife-15224-resp-fig1-v2.tif',
                                      u'elife-15224-fig5-figsupp1-v1.tif': u'elife-15224-fig5-figsupp1-v2.tif',
                                      u'elife-15224-v1.pdf': u'elife-15224-v2.pdf',
                                      u'elife-15224-fig1-figsupp2-v1.tif': u'elife-15224-fig1-figsupp2-v2.tif',
                                      u'elife-15224-fig3-figsupp1-v1.tif': u'elife-15224-fig3-figsupp1-v2.tif',
                                      u'elife-15224-fig1-v1.tif': u'elife-15224-fig1-v2.tif',
                                      u'elife-15224-fig2-v1.tif': u'elife-15224-fig2-v2.tif',
                                      u'elife-15224-fig2-figsupp2-v1.tif': u'elife-15224-fig2-figsupp2-v2.tif',
                                      u'elife-15224-fig5-v1.tif': u'elife-15224-fig5-v2.tif',
                                      u'elife-15224-v1.xml': u'elife-15224-v2.xml',
                                      u'elife-15224-media1-code1-v1.wrl': u'elife-15224-media1-code1-v2.wrl',
                                      u'elife-15224-media.mp4': u'elife-15224-media.mp4',
                                      u'elife-15224-media1.mov': u'elife-15224-media1.mov',
                                      u'elife-15224-resp-media1.avi': u'elife-15224-resp-media1.avi'}


@ddt
class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.applyversionnumber = activity_ApplyVersionNumber(settings_mock, None, None, None, None)
        self.test_dest_folder = 'tests/files_dest_ApplyVersionNumber'
        helpers.create_folder(self.test_dest_folder)

    def tearDown(self):
        helpers.delete_folder(self.test_dest_folder, True)

    @patch.object(activity_ApplyVersionNumber, 'emit_monitor_event')
    @patch('activity.activity_ApplyVersionNumber.get_session')
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
          {'key_names': example_key_names_with_version, 'version': '2', 'expected': example_file_name_map_with_version})
    def test_build_file_name_map(self, key_names, version, expected):
        result = self.applyversionnumber.build_file_name_map(key_names, version)
        self.assertDictEqual(result, expected)

    @unpack
    @data(
        {'file': u'elife-15224.xml', 'version': '1', 'expected': u'elife-15224-v1.xml'},
        {'file': u'elife-code1.tar.gz', 'version': '1', 'expected': u'elife-code1-v1.tar.gz'},
        {'file': u'elife-15224-v1.xml', 'version': '1', 'expected': u'elife-15224-v1.xml'},
        {'file': u'elife-15224-v1.xml', 'version': '2', 'expected': u'elife-15224-v2.xml'},
        {'file': u'elife-code1-v1.tar.gz', 'version': '2', 'expected': u'elife-code1-v2.tar.gz'}
        )
    def test_new_filename(self, file, version, expected):
        result = self.applyversionnumber.new_filename(file, version)
        self.assertEqual(result, expected)

    @unpack
    @data({'file': u'elife-15224-v1.xml', 'expected': u'elife-15224-v1-rewritten.xml'},
          {'file': u'simple-jats-doctype-1.1d3.xml', 'expected': u'simple-jats-doctype-1.1d3.xml'},
          {'file': u'simple-jats-doctype-1.1.xml', 'expected': u'simple-jats-doctype-1.1.xml'})
    def test_rewrite_xml_file(self, file, expected):
        # Patch here in order to use ddt data
        patcher = patch('activity.activity_ApplyVersionNumber.path.join')
        mock_path_join = patcher.start()

        #given
        shutil.copy(u'tests/files_source/ApplyVersionNumber/'+ file, u'tests/files_dest_ApplyVersionNumber/'+ file)
        mock_path_join.return_value = u'tests/files_dest_ApplyVersionNumber/'+ file

        #when
        self.applyversionnumber.rewrite_xml_file(file, example_file_name_map)

        #then
        with open(u'tests/files_dest_ApplyVersionNumber/'+ file, 'r') as result_file:
            result_file_content = result_file.read()
        with open(u'tests/files_source/ApplyVersionNumber/' + expected, 'r') as expected_file:
            expected_file_content = expected_file.read()
        self.assertEqual(result_file_content, expected_file_content)

        patcher.stop()

    @patch('activity.activity_ApplyVersionNumber.path.join')
    def test_rewrite_xml_file_no_changes(self, mock_path_join):
        #given
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

if __name__ == '__main__':
    unittest.main()
