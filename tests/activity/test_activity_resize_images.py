import unittest
from activity.activity_ResizeImages import activity_ResizeImages
import settings_mock
from mock import mock, patch
from classes_mock import FakeSession
import test_activity_data as testdata
import helpers
import classes_mock
import shutil
import unicodedata
from PIL import Image


class TestResizeImages(unittest.TestCase):
    resize_images_start_folder = 'tests/resizeimages_start/'
    resize_images_start_path_and_file = resize_images_start_folder + testdata.session_example['expanded_folder'] + '/elife-00353-vor-v1-20121213000000.zip'
    image_prefix = 'elife-00353-fig1-v1'

    def setUp(self):
        self.resizeimages = activity_ResizeImages(settings_mock, None, None, None, None)
        helpers.create_folder('tests/test_cdn')
        helpers.create_folder(self.resize_images_start_folder + testdata.session_example['expanded_folder'])
        shutil.copy('tests/files_source/elife-00353-fig1-v1.tif', self.resize_images_start_folder + testdata.session_example['expanded_folder'] + '/elife-00353-fig1-v1.tif')
        shutil.copy('tests/files_source/elife-00353-v1.pdf', self.resize_images_start_folder + testdata.session_example['expanded_folder'] + '/elife-00353-v1.pdf')
        shutil.copy('tests/files_source/elife-00353-v1.xml', self.resize_images_start_folder + testdata.session_example['expanded_folder'] + '/elife-00353-v1.xml')

    def tearDown(self):
        helpers.delete_folder('tests/test_cdn', True)
        helpers.delete_folder(self.resize_images_start_folder, True)

    @patch.object(activity_ResizeImages, 'get_file_pointer')
    @patch.object(activity_ResizeImages, 'store_in_cdn')
    @patch.object(activity_ResizeImages, 'get_file_infos')
    @patch('activity.activity_ResizeImages.Session')
    def test_do_activity(self, mock_session, mock_get_file_infos, mock_store_in_cdn, mock_get_file_pointer):
        mock_session.return_value = FakeSession(testdata.session_example)

        mock_get_file_infos.return_value = self.fake_get_file_infos()
        mock_store_in_cdn.side_effect = self.load_to_cdn
        mock_get_file_pointer.side_effect = self.fake_get_file_pointer

        self.resizeimages.emit_monitor_event = mock.MagicMock()
        self.resizeimages.logger = mock.MagicMock()

        success = self.resizeimages.do_activity(testdata.ResizeImages_data)
        self.assertEqual(True, success)

        formats = self.resizeimages.get_formats('Figure')
        prefix = self.image_prefix #this is the name of the file (without extension) that is an image inside files_source folder
        for format_spec_name in formats:
                if format_spec_name != 'Original':
                    format_spec = formats[format_spec_name]
                    suffix = format_spec['suffix']
                    width = format_spec['width']
                    fname = 'tests/test_cdn/' + prefix + suffix + '.' + format_spec['format']
                    real_width, real_height = self.get_image_dimensions(fname)
                    self.assertEqual(width, real_width)

    def load_to_cdn(self, filename, image, cdn_path, download):
        with open('tests/test_cdn/' + filename, 'w') as fd:
            image.seek(0)
            shutil.copyfileobj(image, fd)

    def fake_get_file_pointer(self, key):
        path = self.resize_images_start_folder + unicodedata.normalize('NFKD',key.name).encode('ascii','ignore')
        fp = open(path, 'r')
        return fp

    def fake_get_file_infos(self):
        file_infos = []
        for key_name in testdata.key_names:
            key = FakeKey()
            key.name = key_name
            file_info = classes_mock.FakeFileInfo()
            file_info.key = key
            file_infos.append(file_info)
        bucket = classes_mock.FakeBucket()
        return bucket, file_infos

    def get_image_dimensions(self, fname):
        try:
            with Image.open(fname) as im:
                width, height = im.size
            return width, height
        except Exception as e:
            return


class FakeKey:

    def __init__(self):
        self.name = u''
        self.key = u''

    def get_file(self, param):
        pass

if __name__ == '__main__':
    unittest.main()
