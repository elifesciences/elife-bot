import unittest
from lax_response_adapter import LaxResponseAdapter
from mock import Mock
import json

fake_lax_message = json.dumps({"status": "published",
                               "requested-action": "publish",
                               "datetime": "2013-03-26T00:00:00+00:00",
                               "token": "eyJzdGF0dXMiOiAidm9yIiwgImV4cGFuZGVkX2ZvbGRlciI6ICI4Mzc0MTE0NTUuMS9hOGJiMDVk\nZi0yZGY5LTRmY2UtOGY5Zi0yMTlhY2EwYjAxNDgiLCAiZWlmX2xvY2F0aW9uIjogIjgzNzQxMTQ1\nNS4xL2E4YmIwNWRmLTJkZjktNGZjZS04ZjlmLTIxOWFjYTBiMDE0OC9lbGlmZS04Mzc0MTE0NTUt\ndjEuanNvbiIsICJ2ZXJzaW9uIjogIjEiLCAicnVuIjogImE4YmIwNWRmLTJkZjktNGZjZS04Zjlm\nLTIxOWFjYTBiMDE0OCJ9\n",
                               "id": "837411455"})

workflow_message_expected = {'workflow_data':
                                 {'article_id': u'837411455',
                                  'eif_location': u'837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148/elife-837411455-v1.json',
                                  'expanded_folder': u'837411455.1/a8bb05df-2df9-4fce-8f9f-219aca0b0148',
                                  'message': None,
                                  'requested_action': u'publish',
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


if __name__ == '__main__':
    unittest.main()
