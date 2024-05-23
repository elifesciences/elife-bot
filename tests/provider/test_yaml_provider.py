import unittest
from provider import yaml_provider
from tests import settings_mock


class TestLoadConfig(unittest.TestCase):
    "tests for provider.yaml_provider.load_config()"

    def test_load_config(self):
        rules = yaml_provider.load_config(settings_mock)
        self.assertTrue(isinstance(rules, dict))

    def test_load_publication_email_config(self):
        rules = yaml_provider.load_config(
            settings_mock, config_type="publication_email"
        )
        self.assertTrue(isinstance(rules, dict))

    def test_unknown(self):
        "unknown YAML file"
        rules = yaml_provider.load_config(settings_mock, config_type="__unknown")
        self.assertEqual(rules, None)


class TestValueAsList(unittest.TestCase):
    "tests for value_as_list()"

    def test_list(self):
        "test list value"
        value = ["item"]
        self.assertEqual(value, yaml_provider.value_as_list(value))

    def test_str(self):
        "test str value"
        value = "item"
        self.assertEqual([value], yaml_provider.value_as_list(value))

    def test_none(self):
        "test None value"
        value = None
        self.assertEqual([], yaml_provider.value_as_list(value))

    def test_dict(self):
        "test dict value"
        value = {"key": "value"}
        self.assertEqual(None, yaml_provider.value_as_list(value))
