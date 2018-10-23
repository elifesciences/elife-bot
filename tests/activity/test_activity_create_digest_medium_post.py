# coding=utf-8

import unittest
import copy
from mock import patch
from activity.activity_CreateDigestMediumPost import (
    activity_CreateDigestMediumPost as activity_object)
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


ACTIVITY_DATA = {
    "run": "",
    "article_id": "99999",
    "version": "1",
    "status": "vor",
    "expanded_folder": "",
    "run_type": None
}


def digest_activity_data(data, status=None, run_type=None):
    new_data = copy.copy(data)
    if new_data and status:
        new_data["status"] = status
    if new_data and run_type:
        new_data["run_type"] = run_type
    return new_data


class TestCreateDigestMediumPost(unittest.TestCase):

    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)

    def tearDown(self):
        # clean the temporary directory
        self.activity.clean_tmp_dir()

    @patch.object(activity_object, 'emit_monitor_event')
    def test_do_activity(self, fake_emit):
        # copy files into the input directory using the storage context
        fake_emit.return_value = None
        activity_data = digest_activity_data(
            ACTIVITY_DATA
            )
        # do the activity
        result = self.activity.do_activity(activity_data)
        # check assertions
        self.assertEqual(result, activity_object.ACTIVITY_SUCCESS)


if __name__ == '__main__':
    unittest.main()
