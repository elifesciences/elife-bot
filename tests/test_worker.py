import unittest
import json
from tests import settings_mock
import worker


class TestWorker(unittest.TestCase):

    def setUp(self):
        self.activity_json = None
        with open('tests/test_data/activity.json', 'rb') as open_file:
            self.activity_json = json.loads(open_file.read())

    def test_get_task_token(self):
        expected = (
            'AAAAKgAAAAEAAAAAAAAAAiTLU1nb+mIAOocBiGYTsSABMWaY3FM6Ib1SU1w+SRp1WIYxSmbtunYFMcfJs0' +
            'LqS4bYWhNsYZIkrH7XGRwkgqx8IDM9o6m8BT9sQVUM6NRNxsbZlFUxFh1p6vpXVHWt64hB/9WvlrF8qWNR' +
            '+gx9HTkCHJyfEdsk+3PFCjApQ6+YBtdZLmRw3iHLVT45LvuFnwdBCP+bk5ACOcYi8hcm89qVKMBjtLjZTD' +
            'N0BAVyFX1/V+7zFnaEzrqErdcirHBA7/PHdcsYJpA1V37drsAL50N9U6MVMaYWmFlP7IPJPY4M')
        task_token = worker.get_taskToken(self.activity_json)
        self.assertEqual(task_token, expected)

    def test_get_task_token_failure(self):
        task_token = worker.get_taskToken({})
        self.assertIsNone(task_token)

    def test_get_activity_type(self):
        expected = 'Sum'
        activity_type = worker.get_activityType(self.activity_json)
        self.assertEqual(activity_type, expected)

    def test_get_activity_type_failure(self):
        activity_type = worker.get_activityType({})
        self.assertIsNone(activity_type)

    def test_get_input(self):
        expected = {'data': [1, 3, 7, 11]}
        worker_input = worker.get_input(self.activity_json)
        self.assertEqual(worker_input, expected)

    def test_get_input_failure(self):
        worker_input = worker.get_input({})
        self.assertIsNone(worker_input)

    def test_get_activity_name(self):
        activity_type = 'PingWorker'
        expected = 'activity_PingWorker'
        activity_name = worker.get_activity_name(activity_type)
        self.assertEqual(activity_name, expected)

    def test_import_activity_class(self):
        activity_name = 'activity_PingWorker'
        result = worker.import_activity_class(activity_name)
        self.assertTrue(result)

    def test_import_activity_class_failure(self):
        activity_name = 'this_activity_does_not_exist'
        result = worker.import_activity_class(activity_name)
        self.assertFalse(result)

    def test_get_activity_object(self):
        activity_name = 'activity_PingWorker'
        worker.import_activity_class(activity_name)
        activity_object = worker.get_activity_object(
            activity_name, settings_mock, None, None, None, None)
        self.assertEqual(activity_object.__class__.__name__, activity_name)


if __name__ == '__main__':
    unittest.main()
