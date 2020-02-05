import unittest
import starter.starter_helper as starter_helper
import tests.test_data as test_data
import json
from ddt import ddt, data, unpack
from tests.activity.classes_mock import FakeLogger


example_workflow_name = "PostPerfectPublication"
example_workflow_id = lambda fe, version: "PostPerfectPublication_00353." + version + "." + fe


@ddt
class TestStarterHelper(unittest.TestCase):

    @unpack
    @data({'data': test_data.data_published_lax, 'execution': 'lax'},
          {'data': test_data.data_error_lax, 'execution':'lax'},
          {'data': test_data.data_published_website, 'execution':'website'})
    def test_set_workflow_information_lax(self, data, execution):

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = starter_helper.set_workflow_information(
            example_workflow_name,
            "1",
            None,
            data,
            "%s.%s" % (data.get('article_id'), data.get('version')),
            execution)

        self.assertEqual(example_workflow_id(execution, data.get('version')), workflow_id)
        self.assertEqual(example_workflow_name, workflow_name)
        self.assertEqual("1", workflow_version)
        self.assertIsNone(child_policy)
        self.assertEqual("1800", execution_start_to_close_timeout)
        self.assertEqual(json.dumps(data), workflow_input)

    def test_get_starter_module(self):
        "for coverage successful starter module import"
        starter_name = 'starter_PackagePOA'
        module_object = starter_helper.get_starter_module(starter_name, FakeLogger())
        self.assertIsNotNone(module_object)

    def test_get_starter_module_failure(self):
        "for coverage test failure"
        starter_name = 'not_a_starter'
        module_object = starter_helper.get_starter_module(starter_name, FakeLogger())
        self.assertIsNone(module_object)

    def test_import_starter_module_failure(self):
        "for coverage test import failure"
        starter_name = 'not_a_starter'
        return_value = starter_helper.import_starter_module(starter_name, FakeLogger())
        self.assertFalse(return_value)

if __name__ == '__main__':
    unittest.main()
