import unittest
import provider.lax_provider as lax_provider
import tests.settings_mock as settings_mock

from mock import mock, patch

lax_article_versions_response_data = {u'1':
                                          {u'rev4_decision': None, u'date_initial_decision': u'2015-05-06',
                                           u'datetime_record_updated': u'2016-05-24T16:45:13.815502Z',
                                           u'date_initial_qc': u'2015-04-29', u'date_rev3_qc': None,
                                           u'title': u'Multiple abiotic stimuli are integrated in the regulation of rice gene expression under field conditions',
                                           u'decision': u'RVF',
                                           u'version': 1, u'date_rev4_decision': None,
                                           u'rev3_decision': None,
                                           u'datetime_record_created': u'2016-02-24T15:11:51.831000Z',
                                           u'type': u'research-article', u'status': u'poa', u'date_full_qc': u'2015-05-13',
                                           u'date_rev3_decision': None, u'date_rev1_qc': u'2015-09-17', u'date_rev1_decision': u'2015-10-13',
                                           u'datetime_submitted': None, u'ejp_type': u'RA', u'volume': 4, u'manuscript_id': 8411, u'doi': u'10.7554/eLife.08411',
                                           u'initial_decision': u'EF', u'rev1_decision': u'RVF', u'rev2_decision': u'AF',
                                           u'date_rev2_qc': u'2015-11-11', u'date_rev2_decision': u'2015-11-25', u'date_rev4_qc': None,
                                           u'date_full_decision': u'2015-06-15', u'website_path': u'content/4/e08411v1',
                                           u'datetime_published': u'2015-11-26T00:00:00Z'},
                                      u'2':
                                          {u'rev4_decision': None, u'date_initial_decision': u'2015-05-06',
                                           u'datetime_record_updated': u'2016-05-24T16:45:13.815502Z', u'date_initial_qc': u'2015-04-29',
                                           u'date_rev3_qc': None,
                                           u'title': u'Multiple abiotic stimuli are integrated in the regulation of rice gene expression under field conditions',
                                           u'decision': u'RVF', u'version': 2, u'date_rev4_decision': None, u'rev3_decision': None,
                                           u'datetime_record_created': u'2016-02-24T15:11:51.831000Z',
                                           u'type': u'research-article', u'status': u'vor', u'date_full_qc': u'2015-05-13', u'date_rev3_decision': None,
                                           u'date_rev1_qc': u'2015-09-17', u'date_rev1_decision': u'2015-10-13', u'datetime_submitted': None,
                                           u'ejp_type': u'RA', u'volume': 4, u'manuscript_id': 8411, u'doi': u'10.7554/eLife.08411',
                                           u'initial_decision': u'EF', u'rev1_decision': u'RVF', u'rev2_decision': u'AF',
                                           u'date_rev2_qc': u'2015-11-11', u'date_rev2_decision': u'2015-11-25', u'date_rev4_qc': None,
                                           u'date_full_decision': u'2015-06-15', u'website_path': u'content/4/e08411v1', u'datetime_published': u'2015-12-31T00:00:00Z'}
                                      }

class TestLaxProvider(unittest.TestCase):

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 200, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(2, version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 404, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual("1", version)

    @patch('provider.lax_provider.article_versions')
    def test_article_highest_version(self, mock_lax_provider_article_versions):
        mock_lax_provider_article_versions.return_value = 500, lax_article_versions_response_data
        version = lax_provider.article_highest_version('08411', settings_mock)
        self.assertEqual(None, version)


if __name__ == '__main__':
    unittest.main()
