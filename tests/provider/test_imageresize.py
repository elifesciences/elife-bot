import unittest
import provider.imageresize as resizer
import provider.article_structure as article_structure
from tests.activity.classes_mock import FakeLogger


FORMATS = {
    "Original": {
        "sources": "tif",
        "format": "jpg",
        "download": "yes"
        }}


class TestImageresize(unittest.TestCase):

    def test_resize(self):
        file_name = 'tests/files_source/elife-00353-fig1-v1.tif'
        info = article_structure.ArticleInfo(file_name)
        format_spec = FORMATS.get('Original')
        new_file_name = None
        image_buffer = None
        expected_file_name = 'tests/files_source/elife-00353-fig1-v1.jpg'
        with open(file_name, 'rb') as open_file:
            new_file_name, image_buffer = resizer.resize(
                format_spec, open_file, info, FakeLogger())
        self.assertEqual(new_file_name, expected_file_name)
        self.assertIsNotNone(image_buffer)
