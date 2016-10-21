import unittest
from mock import patch

class FakeArticleInfo:
    def __init__(self):
        self.article_id = "00353"
        self.full_filename = "elife-00353-v1.zip"

class TestVersionLookup(unittest.TestCase):

    @patch()
    def test_get_version_silent_corrections(self):

        self.assertEqual(True, False)

    def test_get_version_normal_process(self):
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
