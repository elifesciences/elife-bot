import unittest
import provider.s3lib as s3lib
import tests.settings_mock as settings_mock
from mock import mock, patch, MagicMock
from ddt import ddt, data, unpack
from boto.s3.key import Key
from boto.s3.prefix import Prefix


class FakeKey(Key):
    def __init__(self, name):
        self.name = name

class FakePrefix(Prefix):
    def __init__(self, name):
        self.name = name

class FakeBucket(object):
    items = []
    def list(self, prefix=None, delimiter=None, headers=None):
        return self.items


@ddt
class TestProviderS3Lib(unittest.TestCase):

    def setUp(self):
        self.fake_s3_keys = [
            FakeKey('one.xml'),
            FakeKey('one.tif'),
            FakeKey('one.pdf')
        ]
        self.fake_s3_prefixes = [
            FakePrefix('two/')
        ]

    def test_get_s3_key_names_from_bucket(self):
        "simple tests for coverage"
        fake_bucket = FakeBucket()
        fake_bucket.items += self.fake_s3_keys
        fake_bucket.items += self.fake_s3_prefixes
        self.assertEqual(len(s3lib.get_s3_key_names_from_bucket(fake_bucket)), 3)
        self.assertEqual(len(s3lib.get_s3_key_names_from_bucket(
            fake_bucket, file_extensions=['.xml'])), 1)
        self.assertEqual(len(s3lib.get_s3_key_names_from_bucket(
            fake_bucket, file_extensions=['.xml', '.pdf'])), 2)
        self.assertEqual(len(s3lib.get_s3_key_names_from_bucket(
            fake_bucket, key_type='prefix')), 1)


    @data(
        (99999, ['pmc/zip/elife-05-19405.zip'], None),
        (19405, ['pmc/zip/elife-05-19405.zip'], 'pmc/zip/elife-05-19405.zip'),
        (24052, [
            'pmc/zip/elife-06-24052.zip'
            'pmc/zip/elife-06-24052.r1.zip',
            'pmc/zip/elife-06-24052.r2.zip',
        ], 'pmc/zip/elife-06-24052.r2.zip'),
        # strange example below would not normally exist but is for code coverage
        (24052, [
            'pmc/zip/elife-04-24052.zip',
            'pmc/zip/elife-05-24052.zip',
            'pmc/zip/elife-05-24052.r1.zip'
        ], 'pmc/zip/elife-05-24052.r1.zip'),
    )
    @unpack
    def test_latest_pmc_zip_revision(self, doi_id, s3_key_names, expected_s3_key_name):
        self.assertEqual(s3lib.latest_pmc_zip_revision(doi_id, s3_key_names), expected_s3_key_name)


if __name__ == '__main__':
    unittest.main()
