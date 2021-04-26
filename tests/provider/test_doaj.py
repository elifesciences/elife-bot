import unittest
import json
from provider import doaj
from tests import read_fixture


class TestDoajProvider(unittest.TestCase):

    def test_doaj_json(self):
        article_json_string = read_fixture("e65469_article_json.txt", "doaj")
        article_json = json.loads(article_json_string)
        expected = read_fixture("e65469_doaj_json.py", "doaj")
        doaj_json = doaj.doaj_json(article_json)
        self.assertEqual(doaj_json, expected)
