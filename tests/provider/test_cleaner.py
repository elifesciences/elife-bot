import os
import unittest
from mock import patch
from testfixtures import TempDirectory
import wand
from provider import cleaner


class TestCleanerProvider(unittest.TestCase):
    def setUp(self):
        self.directory = TempDirectory()
        self.logfile = os.path.join(self.directory.path, "elifecleaner.log")
        cleaner.log_to_file(self.logfile)

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_pdf_page_count(self):
        file_path = "tests/files_source/elife-00353-v1.pdf"
        page_count = cleaner.parse.pdf_page_count(file_path)
        self.assertEqual(page_count, 2)

    @patch.object(wand.image.Image, "allocate")
    def test_pdf_page_count_exception(self, mock_image_allocate):
        mock_image_allocate.side_effect = wand.exceptions.WandRuntimeError()
        file_path = "tests/files_source/elife-00353-v1.pdf"
        with self.assertRaises(wand.exceptions.WandRuntimeError):
            page_count = cleaner.parse.pdf_page_count(file_path)
        with open(self.logfile, "r") as open_file:
            self.assertEqual(
                open_file.readline(),
                (
                    "ERROR elifecleaner:parse:pdf_page_count: WandRuntimeError "
                    "in pdf_page_count(), imagemagick may not be installed\n"
                ),
            )
