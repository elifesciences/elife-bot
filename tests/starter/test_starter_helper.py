import unittest
import starter.starter_helper as starter_helper
import tests.test_data as test_data
import json
from ddt import ddt, data, unpack


example_workflow_name = "PostPerfectPublication"
example_workflow_id = lambda fe: "PostPerfectPublication_00353." + fe


@ddt
class TestStarterPostPerfectPublication(unittest.TestCase):

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
        workflow_input = starter_helper.set_workflow_information(example_workflow_name,
                                                                              "1",
                                                                              None,
                                                                              data)

        self.assertEqual(example_workflow_id(execution), workflow_id)
        self.assertEqual(example_workflow_name, workflow_name)
        self.assertEqual("1", workflow_version)
        self.assertIsNone(child_policy)
        self.assertEqual("1800", execution_start_to_close_timeout)
        self.assertEqual(json.dumps(data), workflow_input)



if __name__ == '__main__':
    unittest.main()
