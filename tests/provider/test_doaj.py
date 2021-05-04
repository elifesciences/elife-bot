import unittest
import json
import time
from collections import OrderedDict
from mock import patch, MagicMock
from provider import doaj
from tests import read_fixture
import tests.settings_mock as settings_mock
from tests.activity.classes_mock import FakeLogger, FakeResponse


class TestSubstituteMathTags(unittest.TestCase):
    def test_substitute_math_tags(self):
        abstract = 'A <math><mi>β</mi></math> <math id="inf1"><mi>β</mi></math>.'
        expected = "A [Formula: see text] [Formula: see text]."
        self.assertEqual(doaj.substitute_math_tags(abstract), expected)

    def test_substitute_math_tags_none(self):
        abstract = None
        expected = None
        self.assertEqual(doaj.substitute_math_tags(abstract), expected)


class TestDoajProvider(unittest.TestCase):
    def test_doaj_json(self):
        article_json_string = read_fixture("e65469_article_json.txt", "doaj")
        article_json = json.loads(article_json_string)
        expected = read_fixture("e65469_doaj_json.py", "doaj")
        doaj_json = doaj.doaj_json(article_json, settings_mock)
        self.assertEqual(doaj_json, expected)

    def test_doaj_json_no_abstract(self):
        "no error when an article json has no abstract"
        article_json_string = read_fixture("e65469_article_json.txt", "doaj")
        article_json = json.loads(article_json_string)
        del article_json["abstract"]
        doaj_json = doaj.doaj_json(article_json, settings_mock)
        self.assertIsNotNone(doaj_json)


class TestDoajAbstract(unittest.TestCase):
    def test_abstract(self):
        abstract_json = {"content": [{"text": "The abstract.", "type": "paragraph"}]}
        expected = "The abstract."
        self.assertEqual(doaj.abstract(abstract_json), expected)

    def test_abstract_remove_tags(self):
        abstract_json = {
            "content": [
                {
                    "text": (
                        'The abstract. <span class="underline">B</span> '
                        '<span class="small-caps">ON</span> '
                        '<span class="monospace">Bonsai</span> '
                        "(within 15 ms, &gt;100 FPS) "
                        '(<a href="#bib34">Lin et al., 2017</a>).'
                    ),
                    "type": "paragraph",
                }
            ]
        }
        expected = (
            "The abstract. B ON Bonsai (within 15 ms, &gt;100 FPS) (Lin et al., 2017)."
        )
        self.assertEqual(doaj.abstract(abstract_json), expected)

    def test_abstract_structured(self):
        abstract_json = {
            "content": [
                {
                    "content": [
                        {
                            "text": "Malaria ....",
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs1",
                    "title": "Background:",
                    "type": "section",
                },
                {
                    "content": [
                        {
                            "text": "In a single centre, ....",
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs2",
                    "title": "Methods:",
                    "type": "section",
                },
                {
                    "content": [
                        {
                            "text": "Mature gametocytes ....",
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs3",
                    "title": "Results:",
                    "type": "section",
                },
                {
                    "content": [
                        {
                            "text": "The early appearance ....",
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs4",
                    "title": "Conclusions:",
                    "type": "section",
                },
                {
                    "content": [
                        {
                            "text": "Funded by PATH Malaria Vaccine Initiative (MVI).",
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs5",
                    "title": "Funding:",
                    "type": "section",
                },
                {
                    "content": [
                        {
                            "text": '<a href="https://clinicaltrials.gov/show/NCT02836002">NCT02836002</a>.',
                            "type": "paragraph",
                        }
                    ],
                    "id": "abs6",
                    "title": "Clinical trial number:",
                    "type": "section",
                },
            ]
        }
        expected = (
            "Background: Malaria ....\n"
            "Methods: In a single centre, ....\n"
            "Results: Mature gametocytes ....\n"
            "Conclusions: The early appearance ....\n"
            "Funding: Funded by PATH Malaria Vaccine Initiative (MVI).\n"
            "Clinical trial number: NCT02836002."
        )
        self.assertEqual(doaj.abstract(abstract_json), expected)

    def test_abstract_maths(self):
        abstract_json = {
            "content": [
                {
                    "text": 'Darwinian fitness ... <math id="inf1"><mi>β</mi></math>-lactamase.',
                    "type": "paragraph",
                }
            ]
        }
        expected = "Darwinian fitness ... [Formula: see text]-lactamase."
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

    def test_author_group(self):
        authors_json = [
            {
                "affiliations": [
                    {
                        "address": {
                            "components": {
                                "country": "United Kingdom",
                                "locality": ["London"],
                            },
                            "formatted": ["London", "United Kingdom"],
                        },
                        "name": [
                            "Centre for Mathematical Modelling of Infectious Diseases, Department of Infectious Disease Epidemiology, Faculty of Epidemiology and Population Health, London School of Hygiene and Tropical Medicine"
                        ],
                    }
                ],
                "name": "CMMID COVID-19 Working Group",
                "type": "group",
            }
        ]
        expected = [
            OrderedDict(
                [
                    (
                        "affiliation",
                        "Centre for Mathematical Modelling of Infectious Diseases, "
                        "Department of Infectious Disease Epidemiology, Faculty of "
                        "Epidemiology and Population Health, London School of Hygiene "
                        "and Tropical Medicine, London, United Kingdom",
                    ),
                    ("name", "CMMID COVID-19 Working Group"),
                ]
            )
        ]
        self.assertEqual(doaj.author(authors_json), expected)

    def test_author_on_behalf_of(self):
        authors_json = [
            {
                "onBehalfOf": "for the HIV Genome-to-Genome Study and the Swiss HIV Cohort Study",
                "type": "on-behalf-of",
            }
        ]
        expected = [
            OrderedDict(
                [
                    (
                        "name",
                        "for the HIV Genome-to-Genome Study and the Swiss HIV Cohort Study",
                    ),
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
        self.assertEqual(
            doaj.identifier(article_json, settings_mock.journal_eissn), expected
        )

    def test_identifier_all(self):
        article_json = {"doi": "10.7554/eLife.65469", "elocationId": "e65469"}
        expected = [
            OrderedDict([("id", "10.7554/eLife.65469"), ("type", "doi")]),
            OrderedDict([("id", "2050-084X"), ("type", "eissn")]),
            OrderedDict([("id", "e65469"), ("type", "elocationid")]),
        ]
        self.assertEqual(
            doaj.identifier(article_json, settings_mock.journal_eissn), expected
        )


class TestDoajJournal(unittest.TestCase):
    def test_journal(self):
        article_json = {"volume": 10}
        expected = OrderedDict([("volume", "10")])
        self.assertEqual(doaj.journal(article_json), expected)


class TestDoajKeywords(unittest.TestCase):
    def test_keywords(self):
        # maximum number of keywords per article is six
        keywords_json = [
            "integrated stress response",
            "remyelination",
            "interferon gamma",
            "oligodendrocyte",
            "cuprizone",
            "multiple sclerosis",
            "seventh keyword",
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

    def test_keywords_italic(self):
        keywords_json = [
            "<i>eLife</i>",
        ]
        expected = [
            "eLife",
        ]
        self.assertEqual(doaj.keywords(keywords_json), expected)


class TestDoajLink(unittest.TestCase):
    def test_link(self):
        article_json = {"id": "65469"}
        expected = [
            OrderedDict(
                [
                    ("content_type", "text/html"),
                    ("type", "fulltext"),
                    ("url", "https://elifesciences.org/articles/65469"),
                ]
            )
        ]
        self.assertEqual(
            doaj.link(article_json, settings_mock.doaj_url_link_pattern), expected
        )


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

    def test_title_tag_removal(self):
        title = "Sample title, <i>PTPRG</i> CUT&RUN HCO<sub>3</sub><sup>–</sup>-dependent <b>τ</b>"
        article_json = {"title": title}
        expected = "Sample title, PTPRG CUT&RUN HCO3–-dependent τ"
        self.assertEqual(doaj.title(article_json), expected)


class TestDoajYear(unittest.TestCase):
    def test_year(self):
        published_date = time.strptime("2021-03-23T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        expected = "2021"
        self.assertEqual(doaj.year(published_date), expected)


class TestDoajPostRequest(unittest.TestCase):
    def setUp(self):
        self.url = settings_mock.doaj_endpoint
        self.api_key = settings_mock.doaj_api_key
        self.logger = FakeLogger()
        self.article_id = "00003"
        self.response_content_success = (
            b'{"status": "created", "id": "26ce51c630d04c8c8664410488150acc", '
            b'"location": "/api/v2/articles/26ce51c630d04c8c8664410488150acc"}'
        )

    @patch("requests.post")
    def test_doaj_post_request_201(self, mock_requests_post):
        verify_ssl = False
        data = {}
        response_status_code = 201
        response = FakeResponse(response_status_code)
        response.content = self.response_content_success
        mock_requests_post.return_value = response

        doaj.doaj_post_request(
            self.url, self.article_id, data, self.api_key, verify_ssl, self.logger
        )

        self.assertEqual(
            self.logger.loginfo[-1],
            "Response from DOAJ API: %s\n%s"
            % (response_status_code, self.response_content_success),
        )
        self.assertEqual(
            self.logger.loginfo[-2],
            "Post article %s to DOAJ API: POST %s\n%s"
            % (self.article_id, self.url, data),
        )

    @patch("requests.post")
    def test_doaj_post_request_400(self, mock_requests_post):
        verify_ssl = False
        data = {}
        response = FakeResponse(400)
        mock_requests_post.return_value = response
        self.assertRaises(
            Exception,
            doaj.doaj_post_request,
            self.url,
            self.article_id,
            data,
            self.api_key,
            verify_ssl,
            self.logger,
        )
