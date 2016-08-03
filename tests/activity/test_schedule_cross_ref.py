import unittest
from activity.activity_ScheduleCrossref import activity_ScheduleCrossref
import settings_mock


class TestsScheduleCrossRef(unittest.TestCase):
    def setUp(self):
        self.schedulecrossref = activity_ScheduleCrossref(settings_mock, None, None, None, None)

    def test_new_crossref_xml_name(self):
        result = self.schedulecrossref.new_crossref_xml_name(self.schedulecrossref.crossref_outbox_folder,
                                                             'elife',
                                                              str('00353').zfill(5))

        self.assertEqual(result, 'crossref/outbox/elife00353.xml')

    def test_new_crossref_xml_name_type_error(self):
        result = self.schedulecrossref.new_crossref_xml_name(self.schedulecrossref.crossref_outbox_folder,
                                                             'elife',
                                                              353)
        self.assertRaises(TypeError)


if __name__ == '__main__':
    unittest.main()
