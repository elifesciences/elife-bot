import unittest
from starter.starter_PostPerfectPublication import starter_PostPerfectPublication
import tests.test_data as test_data
import json
from ddt import ddt, data, unpack


example_workflow_name = "PostPerfectPublication"
example_process_id = "00000"
example_workflow_id = lambda fe: "PostPerfectPublication_00353.00000." + fe


@ddt
class TestStarterPostPerfectPublication(unittest.TestCase):
    def setUp(self):
        self.postperfectpublication = starter_PostPerfectPublication()

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
        workflow_input = self.postperfectpublication.set_workflow_information(example_workflow_name,
                                                                              "1",
                                                                              None,
                                                                              data,
                                                                              example_process_id)

        self.assertEqual(example_workflow_id(execution), workflow_id)
        self.assertEqual(example_workflow_name, workflow_name)
        self.assertEqual("1", workflow_version)
        self.assertIsNone(child_policy)
        self.assertEqual("1800", execution_start_to_close_timeout)
        self.assertEqual(json.dumps(data), workflow_input)



if __name__ == '__main__':
    unittest.main()
