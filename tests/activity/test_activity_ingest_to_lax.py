import unittest
from activity.activity_IngestToLax import activity_IngestToLax
import settings_mock
from ddt import ddt, data
from mock import patch
from classes_mock import FakeLogger

data_example = {
    "article_id": "00353",
    "update_date": "2016-10-05T10:31:54Z",
    "expanded_folder": "00353.1/bb2d37b8-e73c-43b3-a092-d555753316af",
    "message": None,
    "requested_action": "ingest",
    "result": "ingested",
    "run": "bb2d37b8-e73c-43b3-a092-d555753316af",
    "status": "vor",
    "version": "1"
}

@ddt
class TestIngestToLax(unittest.TestCase):
    def setUp(self):
        self.ingesttolax = activity_IngestToLax(settings_mock, None, None, None, None)

    @data(data_example)
    @patch('provider.lax_provider.prepare_action_message')
    def test_do_activity_success(self, data, fake_action_message):
        fake_action_message.return_value = {"example_message": True}

        message, queue, start_event, end_event, end_event_details, exception = self.ingesttolax.get_message_queue(data)
        self.assertEqual(queue, settings_mock.xml_info_queue)
        self.assertEqual(start_event, [settings_mock, data['article_id'], data['version'], data['run'],
                                       self.ingesttolax.pretty_name, "start",
                                       "Starting preparation of article for Lax " + data['article_id']])
        self.assertEqual(end_event, "end")
        self.assertEqual(end_event_details, [settings_mock, data['article_id'], data['version'], data['run'],
                                             self.ingesttolax.pretty_name, "end",
                                             "Finished preparation of article for Lax. "
                                             "Ingest sent to Lax" + data['article_id']])
        self.assertIsNone(exception)

    @data(data_example)
    @patch("provider.lax_provider.prepare_action_message")
    def test_do_activity_error(self, data, fake_lax_provider):
        fake_lax_provider.side_effect = Exception("Access Denied")
        self.ingesttolax = activity_IngestToLax(settings_mock, FakeLogger(), None, None, None)
        message, queue, start_event, end_event, end_event_details, exception = self.ingesttolax.get_message_queue(data)
        self.assertEqual(end_event, "error")
        self.assertEqual(exception, "Access Denied")
        self.assertListEqual(end_event_details, [settings_mock, data['article_id'], data['version'], data['run'],
                                                 self.ingesttolax.pretty_name, "error",
                                                 "Error preparing or sending message to lax" + data['article_id'] +
                                                 " message: Access Denied"])


    @data(data_example)
    def test_do_activity_not_consider_lax(self, data):

        message, queue, start_event, end_event, end_event_details, exception = self.ingesttolax.get_message_queue(data, False)
        self.assertDictEqual(message, {
                                "workflow_name": "ProcessArticleZip",
                                "workflow_data": {
                                    "run":data['run'] ,
                                    "article_id": data['article_id'],
                                    "result": "",
                                    "status": data['status'],
                                    "version": data['version'],
                                    "expanded_folder": data['expanded_folder'],
                                    "requested_action": "",
                                    "message": "",
                                    "update_date": data['update_date']
                                }
                            })
        self.assertEqual(queue, settings_mock.workflow_starter_queue)
        self.assertEqual(start_event, [settings_mock, data['article_id'], data['version'], data['run'],
                                       self.ingesttolax.pretty_name + " (Skipping)", "start",
                                       "Starting preparation of article " + data['article_id']])
        self.assertEqual(end_event, "end")
        self.assertEqual(end_event_details, [settings_mock, data['article_id'], data['version'], data['run'],
                                             self.ingesttolax.pretty_name + " (Skipping)", "end",
                                             "Lax is not being considered, this activity just triggered next "
                                             "workflow without influence from Lax."])


if __name__ == '__main__':
    unittest.main()
