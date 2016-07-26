import unittest
from ddt import ddt, data
import settings_mock
from activity.activity_ApplyVersionNumber import activity_ApplyVersionNumber
from mock import mock, patch
import test_activity_data as test_data
from classes_mock import FakeSession
import shutil
import helpers

example_file_name_map = {u'elife-15224-fig2-figsupp1.tif': u'elife-15224-fig2-figsupp1-v1.tif', u'elife-15224-fig3.tif': u'elife-15224-fig3-v1.tif', u'elife-15224-fig4.tif': u'elife-15224-fig4-v1.tif', u'elife-15224.xml': u'elife-15224-v1.xml', u'elife-15224-resp-fig2.tif': u'elife-15224-resp-fig2-v1.tif', u'elife-15224-fig4-figsupp1.tif': u'elife-15224-fig4-figsupp1-v1.tif', u'elife-15224-resp-fig3.tif': u'elife-15224-resp-fig3-v1.tif', u'elife-15224-figures.pdf': u'elife-15224-figures-v1.pdf', u'elife-15224-resp-fig1.tif': u'elife-15224-resp-fig1-v1.tif', u'elife-15224-fig5-figsupp1.tif': u'elife-15224-fig5-figsupp1-v1.tif', u'elife-15224.pdf': u'elife-15224-v1.pdf', u'elife-15224-fig1-figsupp2.tif': u'elife-15224-fig1-figsupp2-v1.tif', u'elife-15224-fig1-figsupp1.tif': u'elife-15224-fig1-figsupp1-v1.tif', u'elife-15224-fig3-figsupp1.tif': u'elife-15224-fig3-figsupp1-v1.tif', u'elife-15224-fig1.tif': u'elife-15224-fig1-v1.tif', u'elife-15224-fig2.tif': u'elife-15224-fig2-v1.tif', u'elife-15224-fig2-figsupp2.tif': u'elife-15224-fig2-figsupp2-v1.tif', u'elife-15224-fig5.tif': u'elife-15224-fig5-v1.tif'}
example_key_names = [u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1-figsupp2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2-figsupp2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig3.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig4.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5-figsupp1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-fig5.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-figures.pdf', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig1.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig2.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224-resp-fig3.tif', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.pdf', u'15224.1/fec8dcd1-76df-4921-93de-4bf8b8ab70eb/elife-15224.xml']


@ddt
class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.applyversionnumber = activity_ApplyVersionNumber(settings_mock, None, None, None, None)

    @data('elife-15202-poa-v1-20160524113559.zip')
    def test_version_in_file_name(self, with_version):
        result = self.applyversionnumber.version_in_file_name(with_version)
        self.assertNotEqual(result, None)

    @data('elife-15224-vor-r2.zip', 'elife-13567-vor-r1.zip')
    def test_version_in_file_name_no_version(self, no_version):
        result = self.applyversionnumber.version_in_file_name(no_version)
        self.assertEqual(result, None)

    @patch('activity.activity_ApplyVersionNumber.Session')
    def test_do_activity_no_renaming(self, mock_session):
        mock_session.return_value = FakeSession(test_data.session_example)
        self.applyversionnumber.emit_monitor_event = mock.MagicMock()
        result = self.applyversionnumber.do_activity(test_data.ApplyVersionNumber_data_no_renaming)
        self.assertEqual(result, True)

    def test_find_xml_filename_in_map(self):
        new_name = self.applyversionnumber.find_xml_filename_in_map(example_file_name_map)
        self.assertEqual(new_name, u'elife-15224-v1.xml')

    def test_build_file_name_map(self):
        result = self.applyversionnumber.build_file_name_map(example_key_names, '1')
        self.assertDictEqual(result, example_file_name_map)

    def test_new_filename(self):
        result = self.applyversionnumber.new_filename(u'elife-15224.xml','1')
        self.assertEqual(result, u'elife-15224-v1.xml')

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
        result_file = open(u'tests/files_dest_ApplyVersionNumber/elife-15224-v1.xml', 'r')
        result_file_content = result_file.read()
        expected_file = open(u'tests/files_source/ApplyVersionNumber/elife-15224-v1-rewritten.xml', 'r')
        expected_file_content = expected_file.read()
        self.assertEqual(result_file_content, expected_file_content)

        helpers.delete_folder('tests/files_dest_ApplyVersionNumber', True)

if __name__ == '__main__':
    unittest.main()
