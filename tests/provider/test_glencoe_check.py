import unittest
import provider.glencoe_check as glencoe_check
from tests.test_data import glencoe_metadata

class TestGlencoeCheck(unittest.TestCase):

    def test_check_msid_long_id(self):
        result = glencoe_check.check_msid("7777777701234")
        self.assertEqual('01234', result)

    def test_check_msdi_proper_id(self):
        result = glencoe_check.check_msid("01234")
        self.assertEqual('01234', result)

    def test_check_msdi_short_id(self):
        result = glencoe_check.check_msid("34")
        self.assertEqual('00034', result)

    def test_jpg_href_values(self):
        result = glencoe_check.jpg_href_values(glencoe_metadata)
        self.assertItemsEqual(["http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.jpg",
                          "http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.jpg"],
                          result)

    def test_simple_jpg_href_values(self):
        glencoe_metadata = {"media_start1": {"jpg_href": "value1"},
                            "media_start2": {"jpg_href": "value2"},
                            "media_start3": {"no_jpg_href": "value3"},
                            "notmedia": {"jpg_href": "value4"}}
        results = glencoe_check.jpg_href_values(glencoe_metadata)
        self.assertItemsEqual(["value1", "value2"], results)