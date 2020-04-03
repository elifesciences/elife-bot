import unittest
import io
from mock import patch
import wand
import provider.imageresize as resizer
import provider.article_structure as article_structure
from tests.activity.classes_mock import FakeLogger


FORMATS = {
    "Original": {
        "sources": "tif",
        "format": "jpg",
        "download": "yes"
        }}


def image_spec_info(file_name, format_spec='Original'):
    info = article_structure.ArticleInfo(file_name)
    format_spec = FORMATS.get(format_spec)
    return info, format_spec


class TestImageresize(unittest.TestCase):

    def setUp(self):
        self.fake_logger = FakeLogger()

    def test_resize(self):
        file_name = 'tests/files_source/elife-00353-fig1-v1.tif'
        info, format_spec = image_spec_info(file_name)
        new_file_name = None
        image_buffer = None
        expected_file_name = 'tests/files_source/elife-00353-fig1-v1.jpg'
        with open(file_name, 'rb') as open_file:
            new_file_name, image_buffer = resizer.resize(
                format_spec, open_file, info, self.fake_logger)
        self.assertEqual(new_file_name, expected_file_name)
        self.assertIsNotNone(image_buffer)

    @patch.object(wand.image.Image, 'convert')
    def test_resize_exception_in_convert(self, fake_convert):
        fake_convert.side_effect = Exception('An exception')
        file_name = 'tests/files_source/elife-00353-fig1-v1.tif'
        info, format_spec = image_spec_info(file_name)

        with self.assertRaises(RuntimeError):
            with open(file_name, 'rb') as open_file:
                resizer.resize(
                    format_spec, open_file, info, self.fake_logger)
        self.assertEqual(
            self.fake_logger.logerror,
            'error resizing image tests/files_source/elife-00353-fig1-v1')

    @patch.object(wand.image.Image, 'save')
    def test_resize_exception_in_save(self, fake_save):
        fake_save.side_effect = Exception('An exception')
        file_name = 'tests/files_source/elife-00353-fig1-v1.tif'
        info, format_spec = image_spec_info(file_name)

        with self.assertRaises(RuntimeError):
            with open(file_name, 'rb') as open_file:
                resizer.resize(
                    format_spec, open_file, info, self.fake_logger)
        self.assertEqual(
            self.fake_logger.logerror,
            'error resizing image tests/files_source/elife-00353-fig1-v1')

    @patch.object(wand.image.Image, 'save')
    def test_resize_exception_bad_file(self, fake_save):
        fake_save.side_effect = Exception('An exception')
        file_name = 'tests/files_source/elife-00353-fig1-v1.tif'
        info, format_spec = image_spec_info(file_name)
        # create a bad file that wand.Image will not open
        in_memory_file = io.BytesIO(b'junk')

        with self.assertRaises(RuntimeError):
            resizer.resize(
                format_spec, in_memory_file, info, self.fake_logger)
        self.assertEqual(
            self.fake_logger.logerror,
            'error resizing image tests/files_source/elife-00353-fig1-v1')
