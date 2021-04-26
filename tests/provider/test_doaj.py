import unittest
import json
import time
from collections import OrderedDict
from provider import doaj
from tests import read_fixture


class TestDoajProvider(unittest.TestCase):
    def test_doaj_json(self):
        article_json_string = read_fixture("e65469_article_json.txt", "doaj")
        article_json = json.loads(article_json_string)
        expected = read_fixture("e65469_doaj_json.py", "doaj")
        doaj_json = doaj.doaj_json(article_json)
        self.assertEqual(doaj_json, expected)


class TestDoajAbstract(unittest.TestCase):
    def test_abstract(self):
        abstract_json = {"content": [{"text": "The abstract.", "type": "paragraph"}]}
        expected = "The abstract."
        self.assertEqual(doaj.abstract(abstract_json), expected)


class TestDoajAuthor(unittest.TestCase):
    def test_author_person(self):
        authors_json = [
            {
                "affiliations": [
                    {
                        "address": {
                            "components": {
                                "country": "United States",
                                "locality": ["Chicago"],
                            },
                            "formatted": ["Chicago", "United States"],
                        },
                        "name": [
                            "Department of Neurology, Division of Multiple Sclerosis and Neuroimmunology, Northwestern University Feinberg School of Medicine"
                        ],
                    }
                ],
                "name": {"index": "Chen, Yanan", "preferred": "Yanan Chen"},
                "orcid": "0000-0001-5510-231X",
                "type": "person",
            }
        ]
        expected = [
            OrderedDict(
                [
                    (
                        "affiliation",
                        "Department of Neurology, Division of Multiple Sclerosis and Neuroimmunology, Northwestern University Feinberg School of Medicine, Chicago, United States",
                    ),
                    ("name", "Yanan Chen"),
                    ("orcid_id", "https://orcid.org/0000-0001-5510-231X"),
                ]
            )
        ]
        self.assertEqual(doaj.author(authors_json), expected)


class TestDoajAffiliationString(unittest.TestCase):
    def test_affiliation_string(self):
        aff_json = {
            "address": {
                "components": {
                    "country": "United States",
                    "locality": ["Chicago"],
                },
                "formatted": ["Chicago", "United States"],
            },
            "name": [
                "Department of Neurology, Division of Multiple Sclerosis and Neuroimmunology, Northwestern University Feinberg School of Medicine"
            ],
        }
        expected = "Department of Neurology, Division of Multiple Sclerosis and Neuroimmunology, Northwestern University Feinberg School of Medicine, Chicago, United States"
        self.assertEqual(doaj.affiliation_string(aff_json), expected)


class TestDoajIdentifier(unittest.TestCase):
    def test_identifier_blank(self):
        article_json = {}
        expected = [
            OrderedDict([("id", None), ("type", "doi")]),
            OrderedDict([("id", "2050-084X"), ("type", "eissn")]),
            OrderedDict([("id", None), ("type", "elocationid")]),
        ]
        self.assertEqual(doaj.identifier(article_json), expected)

    def test_identifier_all(self):
        article_json = {"doi": "10.7554/eLife.65469", "elocationId": "e65469"}
        expected = [
            OrderedDict([("id", "10.7554/eLife.65469"), ("type", "doi")]),
            OrderedDict([("id", "2050-084X"), ("type", "eissn")]),
            OrderedDict([("id", "e65469"), ("type", "elocationid")]),
        ]
        self.assertEqual(doaj.identifier(article_json), expected)


class TestDoajJournal(unittest.TestCase):
    def test_journal(self):
        article_json = {"volume": 10}
        expected = OrderedDict([("volume", "10")])
        self.assertEqual(doaj.journal(article_json), expected)


class TestDoajKeywords(unittest.TestCase):
    def test_keywords(self):
        keywords_json = [
            "integrated stress response",
            "remyelination",
            "interferon gamma",
            "oligodendrocyte",
            "cuprizone",
            "multiple sclerosis",
        ]
        expected = [
            "integrated stress response",
            "remyelination",
            "interferon gamma",
            "oligodendrocyte",
            "cuprizone",
            "multiple sclerosis",
        ]
        self.assertEqual(doaj.keywords(keywords_json), expected)


class TestDoajLink(unittest.TestCase):
    def test_link(self):
        article_json = {"id": "65469"}
        expected = OrderedDict(
            [
                ("content_type", "text/html"),
                ("type", "fulltext"),
                ("url", "https://elifesciences.org/articles/65469"),
            ]
        )
        self.assertEqual(doaj.link(article_json), expected)


class TestDoajMonth(unittest.TestCase):
    def test_month(self):
        published_date = time.strptime("2021-03-23T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        expected = "3"
        self.assertEqual(doaj.month(published_date), expected)


class TestDoajTitle(unittest.TestCase):
    def test_title(self):
        title = (
            "Prolonging the integrated stress response enhances CNS remyelination "
            "in an inflammatory environment"
        )
        article_json = {"title": title}
        expected = title
        self.assertEqual(doaj.title(article_json), expected)


class TestDoajYear(unittest.TestCase):
    def test_year(self):
        published_date = time.strptime("2021-03-23T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        expected = "2021"
        self.assertEqual(doaj.year(published_date), expected)
