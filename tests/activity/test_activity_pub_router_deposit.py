import unittest
import os
import shutil
from mock import patch
from ddt import ddt, data, unpack
import provider.s3lib as s3lib
from activity.activity_PubRouterDeposit import activity_PubRouterDeposit
import tests.test_data as test_case_data
import tests.activity.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger


def download_files(filenames, to_dir):
    copied_filenames = []
    for filename in filenames:
        source_doc = "tests/test_data/" + filename
        dest_doc = os.path.join(to_dir, filename)
        try:
            shutil.copy(source_doc, dest_doc)
            copied_filenames.append(dest_doc)
        except IOError:
            pass
    return copied_filenames


@ddt
class TestPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(
            settings_mock, FakeLogger(), None, None, None)

    @patch('provider.lax_provider.article_versions')
    @patch.object(activity_PubRouterDeposit, 'start_ftp_article_workflow')
    @patch.object(activity_PubRouterDeposit, 'does_source_zip_exist_from_s3')
    @patch.object(activity_PubRouterDeposit, 'download_files_from_s3_outbox')
    @patch.object(s3lib, 'get_s3_keys_from_bucket')
    def test_do_activity(self, fake_get_s3_keys, fake_download, fake_zip_exists,
                         fake_start, fake_article_versions):
        activity_data = {
            "data": {
                "workflow": "HEFCE"
            }
        }
        fake_download.return_value = download_files(
            ["elife00013.xml", "elife09169.xml"], self.pubrouterdeposit.get_tmp_dir())
        fake_zip_exists.return_value = True
        fake_start.return_value = True
        fake_article_versions.return_value = 200, test_case_data.lax_article_versions_response_data
        result = self.pubrouterdeposit.do_activity(activity_data)
        self.assertTrue(result)

    # input: s3 archive zip file name (name) and date last modified
    # expected output: file name - highest version file (displayed on -v[number]-)
    # then latest last modified date/time
    @unpack
    @data(
        {
            "s3_keys": [
                {
                    "name": "elife-16747-vor-v1-20160831000000.zip",
                    "last_modified": "2017-05-18T09:04:11.000Z"
                },
                {
                    "name": "elife-16747-vor-v1-20160831132647.zip",
                    "last_modified": "2016-08-31T06:26:56.000Z"
                }
            ],
            "expected": "elife-16747-vor-v1-20160831000000.zip"
            },
        {
            "s3_keys": [
                {
                    "name": "elife-16747-vor-v1-20160831000000.zip",
                    "last_modified": "2017-05-18T09:04:11.000Z"
                },
                {
                    "name": "elife-16747-vor-v1-20160831132647.zip",
                    "last_modified": "2016-08-31T06:26:56.000Z"
                },
                {
                    "name": "elife-16747-vor-v2-20160831000000.zip",
                    "last_modified": "2015-01-05T00:20:50.000Z"
                }
            ],
            "expected": "elife-16747-vor-v2-20160831000000.zip"
            }
        )
    def test_latest_archive_zip_revision(self, s3_keys, expected):
        output = self.pubrouterdeposit.latest_archive_zip_revision("16747", s3_keys, "elife", "vor")
        self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()
