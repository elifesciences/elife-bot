import unittest
from activity.activity_PubRouterDeposit import activity_PubRouterDeposit
import tests.activity.settings_mock as settings_mock
from ddt import ddt, data, unpack

@ddt
class TestPubRouterDeposit(unittest.TestCase):
    def setUp(self):
        self.pubrouterdeposit = activity_PubRouterDeposit(settings_mock, None, None, None, None)

    # input: s3 archive zip file name (name) and date last modified
    # expected output: file name - highest version file (displayed on -v[number]-) then latest last modified date/time
    @unpack
    @data({"input": [{"name": "elife-16747-vor-v1-20160831000000.zip", "last_modified": "2017-05-18T09:04:11.000Z"},
                    {"name": "elife-16747-vor-v1-20160831132647.zip", "last_modified": "2016-08-31T06:26:56.000Z"}],
           "expected": "elife-16747-vor-v1-20160831000000.zip"},
          {"input": [{"name": "elife-16747-vor-v1-20160831000000.zip", "last_modified": "2017-05-18T09:04:11.000Z"},
                    {"name": "elife-16747-vor-v1-20160831132647.zip", "last_modified": "2016-08-31T06:26:56.000Z"},
                    {"name": "elife-16747-vor-v2-20160831000000.zip", "last_modified": "2015-01-05T00:20:50.000Z"}],
           "expected": "elife-16747-vor-v2-20160831000000.zip"}
          )
    def test_latest_archive_zip_revision(self, input, expected):
        output = self.pubrouterdeposit.latest_archive_zip_revision("16747", input, "elife", "vor")
        self.assertEqual(output, expected)


if __name__ == '__main__':
    unittest.main()
