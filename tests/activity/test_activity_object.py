# coding=utf-8

import os
import unittest
from mock import patch
from activity.objects import Activity
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


class TestActivity(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = Activity(settings_mock, fake_logger, None, None, None)
        # create a tmp directory before os.mkdir is potentially mocked
        self.activity.make_tmp_dir()

    def tearDown(self):
        self.activity.directories = None
        self.activity.clean_tmp_dir()

    def tmp_dir_folder_name(self, dir_name):
        return os.path.join(self.activity.get_tmp_dir(), dir_name)

    def test_make_activity_directories_none(self):
        """test creating activity directories with None values"""
        self.assertIsNone(self.activity.make_activity_directories())

    def test_make_activity_directories_new(self):
        """test creating a new activity directory passed as an argument"""
        dir_names = [self.tmp_dir_folder_name('foo'), self.tmp_dir_folder_name('bar')]
        self.assertTrue(self.activity.make_activity_directories(dir_names))

    def test_make_activity_directories_property(self):
        """test creating a new activity directory from object property"""
        self.activity.directories = {"foo": self.tmp_dir_folder_name('foo')}
        self.assertTrue(self.activity.make_activity_directories())

    def test_make_activity_directories_bad_property(self):
        """test bad directories object property"""
        self.activity.directories = ["list_not_supported_here"]
        self.assertIsNone(self.activity.make_activity_directories())
        self.assertTrue(
            self.activity.logger.loginfo.endswith(
                "No dir_names to create in make_activity_directories()"))

    def test_make_activity_directories_exists(self):
        """test creating a new activity directory passed as an argument"""
        dir_name = self.tmp_dir_folder_name('foo')
        os.mkdir(dir_name)
        dir_names = [dir_name]
        self.assertTrue(self.activity.make_activity_directories(dir_names))

    @patch("activity.objects.os.mkdir")
    def test_make_activity_directories_exception(self, fake_mkdir):
        """test creating a new activity directory exception catching"""
        dir_names = [self.tmp_dir_folder_name('foo')]
        fake_mkdir.side_effect = Exception("Something went wrong!")
        self.assertRaises(Exception, self.activity.make_activity_directories, dir_names)


if __name__ == '__main__':
    unittest.main()
