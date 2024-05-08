import unittest
from provider import yaml_provider
from tests import settings_mock


class TestLoadConfig(unittest.TestCase):
    "tests for provider.yaml_provider.load_config()"

    def test_load_config(self):
        rules = yaml_provider.load_config(settings_mock)
        self.assertTrue(isinstance(rules, dict))
