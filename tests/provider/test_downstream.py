import unittest
from collections import OrderedDict
from provider import downstream
from tests import settings_mock


class TestLoadConfig(unittest.TestCase):
    def test_load_config(self):
        rules = downstream.load_config(settings_mock)
        self.assertTrue(isinstance(rules, dict))


class TestFolderMap(unittest.TestCase):
    def test_workflow_s3_bucket_folder_map(self):
        rules = downstream.load_config(settings_mock)
        folder_map = downstream.workflow_s3_bucket_folder_map(rules)
        self.assertTrue(isinstance(folder_map, OrderedDict))
