import unittest
from lax_response_adapter import LaxResponseAdapter
from mock import Mock
import json
import base64

fake_token = json.dumps({u'status': u'vor',
                         u'expanded_folder': u'837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                         u'version': u'1',
                         u'force': False,
                         u'run': u'a8bb05df-2df9-4fce-8f9f-219aca0b0148'})

fake_lax_message = json.dumps({"status": "published",
                               "requested-action": "publish",
                               "datetime": "2013-03-26T00:00:00+00:00",
                               "token": base64.encodestring(fake_token),
                               "id": "837411455"})

workflow_message_expected = {'workflow_data':
                                 {'article_id': u'837411455',
                                  'expanded_folder': u'837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                                  'message': None,
                                  'requested_action': u'publish',
                                  'force': False,
                                  'result': u'published',
                                  'run': u'a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                                  'status': u'vor',
                                  'update_date': '2013-03-26T00:00:00Z',
                                  'version': u'1'},
                             'workflow_name': 'PostPerfectPublication'}

fake_token_269 = json.dumps({u'status': u'vor',
                         u'expanded_folder': u'00269.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                         u'version': u'1',
                         u'force': False,
                         u'run': u'a8bb05df-2df9-4fce-8f9f-219aca0b0148'})

fake_lax_message_269 = json.dumps({"status": "published",
                               "requested-action": "publish",
                               "datetime": "2013-03-26T00:00:00+00:00",
                               "token": base64.encodestring(fake_token_269),
                               "id": "269"})

workflow_message_expected_269 = {'workflow_data':
                                 {'article_id': u'00269',
                                  'expanded_folder': u'00269.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                                  'message': None,
                                  'requested_action': u'publish',
                                  'force': False,
                                  'result': u'published',
                                  'run': u'a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                                  'status': u'vor',
                                  'update_date': '2013-03-26T00:00:00Z',
                                  'version': u'1'},
                             'workflow_name': 'PostPerfectPublication'}

class TestLaxResponseAdapter(unittest.TestCase):
    def setUp(self):
        settings = Mock()
        self.logger = Mock()
        self.laxresponseadapter = LaxResponseAdapter(settings, self.logger)

    def test_parse_message(self):
        expected_workflow_starter_message = self.laxresponseadapter.parse_message(fake_lax_message)
        self.assertDictEqual.__self__.maxDiff = None
        self.assertDictEqual(expected_workflow_starter_message, workflow_message_expected)

    def test_parse_message_269(self):
        expected_workflow_starter_message = self.laxresponseadapter.parse_message(fake_lax_message_269)
        self.assertDictEqual.__self__.maxDiff = None
        self.assertDictEqual(expected_workflow_starter_message, workflow_message_expected_269)

if __name__ == '__main__':
    unittest.main()
