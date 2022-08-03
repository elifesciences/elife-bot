import unittest
import provider.glencoe_check as glencoe_check
from tests.test_data import glencoe_metadata


class TestGlencoeCheck(unittest.TestCase):
    def test_check_msid_long_id(self):
        cases = [
            # the last six digits are extracted
            ("7777777777777", "777777"),
            ("7777777701234", "701234"),

            # `pad_msid` is called on the substring and leading zeros are truncated to 5 at most.
            ("7000000001234", "01234"),

            # five digit MSIDs are preserved
            ("01234", "01234"),

            # unpadded MSIDs are padded
            ("34", "00034"),

            # the kitchen sink is a special case
            ("91234567890", "1234567890"),

            # regular integers are handled
            (123, "00123"),
            (12345, "12345"),
            (123456, "123456"),
            (111222333, "222333"), # (last six digits extracted)
        ]
        for given, expected in cases:
            self.assertEqual(glencoe_check.check_msid(given), expected)

    def test_jpg_href_values(self):
        result = glencoe_check.jpg_href_values(glencoe_metadata)
        self.assertCountEqual(
            [
                (
                    "http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/"
                    "1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.jpg"
                ),
                (
                    "http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/"
                    "1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.jpg"
                ),
            ],
            result,
        )

    def test_simple_jpg_href_values(self):
        glencoe_metadata = {
            "media_start1": {"jpg_href": "value1"},
            "media_start2": {"jpg_href": "value2"},
            "media_start3": {"no_jpg_href": "value3"},
            "anything_else": {"jpg_href": "value4"},
        }
        results = glencoe_check.jpg_href_values(glencoe_metadata)
        self.assertCountEqual(["value1", "value2", "value4"], results)

    def test_extend_article_for_end2end(self):
        filename = "elife-01234-media1-v1.jpg"
        article_id = "7777777701234"
        result = glencoe_check.force_article_id(filename, article_id)
        self.assertEqual("elife-7777777701234-media1-v1.jpg", result)

    def test_has_videos(self):
        cases = [
            (
                '<media content-type="glencoe play-in-place height-250 width-310" id="media1"'
                ' mime-subtype="avi" mimetype="video" xlink:href="elife-00007-media1.avi"></media>',
                True,
            ),
            (
                '<media mimetype="video" mime-subtype="mp4" id="fig3video1"'
                ' xlink:href="elife-00666-fig3-video1.mp4"></media>',
                True,
            ),
            (
                '<media mimetype="video" mime-subtype="gif" id="video2"'
                ' xlink:href="elife-00666-video2.gif"></media>',
                True,
            ),
            (
                '<media mimetype="application" mime-subtype="xlsx"'
                ' xlink:href="elife-00666-video1-data1.xlsx"/>'
                '<media mimetype="video" mime-subtype="gif" id="video2"'
                ' xlink:href="elife-00666-video2.gif"></media>',
                True,
            ),
            (
                '<media mimetype="application" mime-subtype="xlsx"'
                ' xlink:href="elife-00666-video1-data1.xlsx"/>',
                False,
            ),
            (
                b'<media mimetype="video" mime-subtype="gif" id="video2"'
                b' xlink:href="elife-00666-video2.gif"></media>',
                True,
            ),
        ]
        for xml_str, expected in cases:
            self.assertEqual(glencoe_check.has_videos(xml_str), expected)


class TestGlencoeCheckValidateSources(unittest.TestCase):
    def test_validate_sources_empty(self):
        gc_data = {}
        try:
            glencoe_check.validate_sources(gc_data)
        except AssertionError:
            self.fail("Encountered an unexpected exception.")

    def test_validate_sources_good(self):
        """all video sources available is good, does not raise an exception"""
        gc_data = {
            "video1": {"mp4_href": "", "webm_href": "", "ogv_href": ""},
            "video2": {"mp4_href": "", "webm_href": "", "ogv_href": ""},
        }
        try:
            glencoe_check.validate_sources(gc_data)
        except AssertionError:
            self.fail("Encountered an unexpected exception.")

    def test_validate_sources_bad(self):
        """not enough video sources for a video raises an exception"""
        gc_data = {
            "video1": {"mp4_href": "", "webm_href": "", "ogv_href": ""},
            "video2": {
                "mp4_href": "",
            },
        }
        with self.assertRaises(AssertionError):
            glencoe_check.validate_sources(gc_data)
