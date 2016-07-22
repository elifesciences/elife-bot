import unittest
from ddt import ddt, data
import settings_mock
from activity.activity_ApplyVersionNumber import activity_ApplyVersionNumber
from mock import mock, patch

@ddt
class MyTestCase(unittest.TestCase):
#file_names = [u'elife-15224-vor-r2.zip',u'elife-15224-vor-r2.zip', u'elife-13567-vor-r1.zip']

    def setUp(self):
        self.applyversionnumber = activity_ApplyVersionNumber(settings_mock, None, None, None, None)

    @data('elife-15202-poa-v1-20160524113559.zip')
    def test_version_in_file_name(self, with_version):
        result = self.applyversionnumber.version_in_file_name(with_version)
        self.assertNotEqual(result, None)

    @data('elife-15224-vor-r2.zip', 'elife-13567-vor-r1.zip')
    def test_version_in_file_name_no_version(self, no_version):
        result = self.applyversionnumber.version_in_file_name(no_version)
        self.assertEqual(result, None)

if __name__ == '__main__':
    unittest.main()
