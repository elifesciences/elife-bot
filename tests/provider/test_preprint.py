# coding=utf-8

import time
import unittest
from xml.etree.ElementTree import Element
from mock import patch
from elifearticle.article import (
    Affiliation,
    Article,
    ArticleDate,
    Contributor,
    Event,
    License,
    Role,
)
from tests import read_fixture, settings_mock
from provider import cleaner, preprint


def anonymous_contributor(contrib_type="author"):
    "instantiate an anonymous Contributor object"
    contributor = Contributor(contrib_type, None, None)
    contributor.anonymous = True
    return contributor


def article_fixture():
    "create an Article object with data for testing"
    article = Article(
        "10.7554/eLife.84364",
        (
            "Opto-RhoGEFs: an optimized optogenetic toolbox to reversibly control "
            "Rho GTPase activity on a global to subcellular scale, enabling "
            "precise control over vascular endothelial barrier strength"
        ),
    )
    article.article_type = "preprint"
    article.manuscript = "84364"
    article.version_doi = "10.7554/eLife.84364.2"
    article.abstract = "An abstract."
    # contributor
    contributor = Contributor("author", "Mahlandt", "Eike K.")
    affiliation = Affiliation()
    affiliation.institution = (
        "Swammerdam Institute for Life Sciences, Section of Molecular Cytology, "
        "van Leeuwenhoek Centre for Advanced Microscopy, University of Amsterdam, "
        "Science Park 904, 1098 XH, Amsterdam"
    )
    affiliation.country = "The Netherlands"
    contributor.set_affiliation(affiliation)
    article.add_contributor(contributor)
    # date
    article.add_date(
        ArticleDate("posted_date", time.strptime("2023-02-13", "%Y-%m-%d"))
    )
    # volume
    article.volume = 12
    # license
    license_object = License()
    license_object.href = "http://creativecommons.org/licenses/by/4.0/"
    article.license = license_object
    # pub-history
    preprint_event = Event()
    preprint_event.event_type = "preprint"
    preprint_event.date = time.strptime("2022-10-17", "%Y-%m-%d")
    preprint_event.uri = "https://doi.org/10.1101/2022.10.17.512253"
    reviewed_preprint_event = Event()
    reviewed_preprint_event.event_type = "reviewed-preprint"
    reviewed_preprint_event.date = time.strptime("2023-02-12", "%Y-%m-%d")
    reviewed_preprint_event.uri = "https://doi.org/10.7554/eLife.84364.1"
    article.publication_history = [preprint_event, reviewed_preprint_event]
    # sub-article data
    sub_article_1 = Article("10.7554/eLife.84364.1.sa0", "eLife assessment")
    sub_article_1.id = "sa0"
    sub_article_1.article_type = "editor-report"
    affiliation = Affiliation()
    affiliation.institution = "University of California"
    affiliation.city = "Berkeley"
    affiliation.country = "United States"
    contributor = Contributor("author", "Eisen", "Michael B")
    contributor.roles = [Role("Reviewing Editor", "editor")]
    contributor.set_affiliation(affiliation)
    sub_article_1.add_contributor(contributor)

    sub_article_2 = Article("10.7554/eLife.84364.1.sa1", "Reviewer #1 (Public Review)")
    sub_article_2.id = "sa1"
    sub_article_2.article_type = "referee-report"
    sub_article_2.add_contributor(anonymous_contributor())

    sub_article_3 = Article("10.7554/eLife.84364.1.sa2", "Reviewer #2 (Public Review)")
    sub_article_3.id = "sa2"
    sub_article_3.article_type = "referee-report"
    sub_article_3.add_contributor(anonymous_contributor())

    sub_article_4 = Article("10.7554/eLife.84364.1.sa3", "Reviewer #3 (Public Review)")
    sub_article_4.id = "sa3"
    sub_article_4.article_type = "referee-report"
    sub_article_4.add_contributor(anonymous_contributor())

    sub_article_5 = Article("10.7554/eLife.84364.1.sa4", "Author response")
    sub_article_5.id = "sa4"
    sub_article_5.article_type = "author-comment"
    contributor = Contributor("author", "Mahlandt", "Eike K.")
    sub_article_5.add_contributor(contributor)

    article.review_articles = [
        sub_article_1,
        sub_article_2,
        sub_article_3,
        sub_article_4,
        sub_article_5,
    ]
    return article


def sub_article_data_fixture():
    "fixture for 84364 docmap and peer review data returned by cleaner.sub_article.sub_article_data()"
    sub_article_1 = Article("10.7554/eLife.84364.2.sa4")
    sub_article_1.article_type = "editor-report"
    sub_article_1.id = "sa4"
    sub_article_1.title = "eLife assessment"
    contributor = Contributor("author", "Eisen", "Michael B")
    contributor.roles = [Role("Reviewing Editor", "editor")]
    # contributor.set_affiliation(affiliation)
    sub_article_1.add_contributor(contributor)

    sub_article_2 = Article("10.7554/eLife.84364.2.sa3")
    sub_article_2.article_type = "referee-report"
    sub_article_2.id = "sa3"
    sub_article_2.title = "Reviewer #1 (Public Review):"

    sub_article_3 = Article("10.7554/eLife.84364.2.sa2")
    sub_article_3.article_type = "referee-report"
    sub_article_3.id = "sa2"
    sub_article_3.title = "Reviewer #2 (Public Review):"

    sub_article_4 = Article("10.7554/eLife.84364.2.sa1")
    sub_article_4.article_type = "referee-report"
    sub_article_4.id = "sa1"
    sub_article_4.title = "Reviewer #3 (Public Review):"

    sub_article_5 = Article("10.7554/eLife.84364.2.sa0")
    sub_article_5.article_type = "author-comment"
    sub_article_5.id = "sa0"
    sub_article_5.title = "Author Response:"

    return [
        {"article": sub_article_1, "xml_root": Element("root")},
        {"article": sub_article_2, "xml_root": Element("root")},
        {"article": sub_article_3, "xml_root": Element("root")},
        {"article": sub_article_4, "xml_root": Element("root")},
        {"article": sub_article_5, "xml_root": Element("root")},
    ]


class TestBuildArticle(unittest.TestCase):
    "tests for preprint.build_article()"

    @patch.object(cleaner, "sub_article_data")
    def test_build_article(self, fake_sub_article_data):
        "test building an Article from docmap and preprint XML inputs"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        article_xml_path = "tests/files_source/epp/data/84364/v2/84364-v2.xml"
        article = preprint.build_article(article_id, docmap_string, article_xml_path)
        # assertions
        self.assertEqual(article.doi, "10.7554/eLife.84364")
        self.assertEqual(article.version_doi, "10.7554/eLife.84364.2")
        self.assertEqual(
            article.get_date("posted_date").date,
            time.strptime("2023-06-14T14:00:00+00:00", "%Y-%m-%dT%H:%M:%S%z"),
        )
        # assertion on publication_history events
        self.assertEqual(len(article.publication_history), 2)
        self.assertEqual(article.publication_history[0].event_type, "preprint")
        self.assertEqual(
            article.publication_history[0].uri,
            "https://doi.org/10.1101/2022.10.17.512253",
        )
        self.assertEqual(article.publication_history[1].event_type, "reviewed-preprint")
        self.assertEqual(
            article.publication_history[1].uri, "https://doi.org/10.7554/eLife.84364.1"
        )
        self.assertEqual(article.volume, 12)
        self.assertIsNotNone(article.license)
        self.assertEqual(
            article.license.href, "http://creativecommons.org/licenses/by/4.0/"
        )
        # metadata from preprint XML
        self.assertEqual(
            article.title,
            (
                "Opto-RhoGEFs: an optimized optogenetic toolbox to reversibly control "
                "Rho GTPase activity on a global to subcellular scale, enabling precise "
                "control over vascular endothelial barrier strength"
            ),
        )
        self.assertTrue(
            article.abstract.startswith(
                "<p>The inner layer of blood vessels consists of endothelial cells,"
            )
        )
        self.assertEqual(len(article.contributors), 6)
        self.assertEqual(len(article.ref_list), 77)
        # review_articles
        self.assertEqual(len(article.review_articles), 5)

        # assertions on the review articles
        self.assertEqual(article.review_articles[0].article_type, "editor-report")
        self.assertEqual(article.review_articles[0].doi, "10.7554/eLife.84364.2.sa4")
        self.assertEqual(article.review_articles[0].id, "sa4")
        self.assertEqual(article.review_articles[0].title, "eLife assessment")
        self.assertEqual(len(article.review_articles[0].contributors), 1)
        self.assertEqual(article.review_articles[0].contributors[0].surname, "Eisen")

        self.assertEqual(article.review_articles[1].article_type, "referee-report")
        self.assertEqual(article.review_articles[1].doi, "10.7554/eLife.84364.2.sa3")
        self.assertEqual(article.review_articles[1].id, "sa3")
        self.assertEqual(
            article.review_articles[1].title, "Reviewer #1 (Public Review):"
        )
        self.assertEqual(len(article.review_articles[1].contributors), 1)

        self.assertEqual(article.review_articles[4].article_type, "author-comment")
        self.assertEqual(article.review_articles[4].doi, "10.7554/eLife.84364.2.sa0")
        self.assertEqual(article.review_articles[4].id, "sa0")
        self.assertEqual(article.review_articles[4].title, "Author Response:")
        self.assertEqual(len(article.review_articles[4].contributors), 6)

    @patch.object(cleaner, "sub_article_data")
    def test_specific_version(self, fake_sub_article_data):
        "test building an Article for a specific version"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        version = 1
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        article_xml_path = "tests/files_source/epp/data/84364/v2/84364-v2.xml"
        article = preprint.build_article(article_id, docmap_string, article_xml_path, version)
        # assertions
        self.assertEqual(article.doi, "10.7554/eLife.84364")
        self.assertEqual(article.version_doi, "10.7554/eLife.84364.1")
        self.assertEqual(
            article.get_date("posted_date").date,
            time.strptime("2023-02-13T14:00:00+00:00", "%Y-%m-%dT%H:%M:%S%z"),
        )
        # assertion on publication_history events
        self.assertEqual(len(article.publication_history), 1)
        self.assertEqual(article.publication_history[0].event_type, "preprint")
        self.assertEqual(
            article.publication_history[0].uri,
            "https://doi.org/10.1101/2022.10.17.512253",
        )

        self.assertIsNotNone(article.license)
        self.assertEqual(
            article.license.href, "http://creativecommons.org/licenses/by/4.0/"
        )

    @patch.object(cleaner, "sub_article_data")
    def test_no_posted_date(self, fake_sub_article_data):
        "test if an exception is raised due to no poasted date"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        # remove the date from the docmap fixture
        docmap_string = docmap_string.replace(
            b'"published": "2023-06-14T14:00:00+00:00",', b""
        )
        article_xml_path = "tests/files_source/epp/data/84364/v2/84364-v2.xml"
        with self.assertRaises(preprint.PreprintArticleException) as test_exception:
            preprint.build_article(article_id, docmap_string, article_xml_path)
        self.assertEqual(
            str(test_exception.exception),
            (
                "Could not find a date in the history events for article_id %s"
                % article_id
            ),
        )

    @patch.object(cleaner, "version_doi_from_docmap")
    def test_no_version_doi(self, fake_version_doi):
        fake_version_doi.return_value = None
        with self.assertRaises(preprint.PreprintArticleException) as test_exception:
            result = preprint.build_article(None, None, None)
            self.assertEqual(result, None)

    @patch.object(cleaner, "version_doi_from_docmap")
    def test_incorrect_version_doi(self, fake_version_doi):
        fake_version_doi.return_value = "10.999999/unwanted.doi"
        with self.assertRaises(preprint.PreprintArticleException) as test_exception:
            result = preprint.build_article(None, None, None)
            self.assertEqual(result, None)


class TestXmlFilename(unittest.TestCase):
    "tests for preprint.xml_filename()"

    def test_xml_filename(self):
        "test with no version argument"
        article_id = "84364"
        expected = "elife-preprint-%s.xml" % article_id
        result = preprint.xml_filename(article_id, settings_mock)
        self.assertEqual(result, expected)

    def test_with_version(self):
        "test with a version argument"
        article_id = "84364"
        version = 2
        expected = "elife-preprint-%s-v%s.xml" % (article_id, version)
        result = preprint.xml_filename(article_id, settings_mock, version)
        self.assertEqual(result, expected)


class TestPreprintXml(unittest.TestCase):
    "tests for preprint.preprint_xml()"

    def test_preprint_xml(self):
        "generate XML from an Article"
        article = article_fixture()
        expected_fragments = [
            (
                b"<!DOCTYPE article\n"
                b' PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.1d3 20150301//EN"\n'
                b'  "JATS-archivearticle1.dtd">'
            ),
            (
                b'<article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" article-type="preprint" dtd-version="1.1d3">'
            ),
            b'<journal-id journal-id-type="nlm-ta">elife</journal-id>',
            b'<journal-id journal-id-type="publisher-id">eLife</journal-id>',
            (
                b"<journal-title-group>\n"
                b"<journal-title>eLife</journal-title>\n"
                b"</journal-title-group>"
            ),
            b'<issn publication-format="electronic">2050-084X</issn>',
            (
                b"<publisher>\n"
                b"<publisher-name>eLife Sciences Publications, Ltd</publisher-name>\n"
                b"</publisher>"
            ),
            (
                b"<article-meta>\n"
                b'<article-id pub-id-type="publisher-id">84364</article-id>\n'
                b'<article-id pub-id-type="doi">10.7554/eLife.84364</article-id>\n'
                b'<article-id pub-id-type="doi" specific-use="version">10.7554/eLife.84364.2</article-id>\n'
            ),
            (
                b"<title-group>\n"
                b"<article-title>Opto-RhoGEFs: an optimized optogenetic toolbox to reversibly control Rho GTPase activity on a global to subcellular scale, enabling precise control over vascular endothelial barrier strength</article-title>\n"
                b"</title-group>"
            ),
            (
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<name>\n"
                b"<surname>Mahlandt</surname>\n"
                b"<given-names>Eike K.</given-names>\n"
                b"</name>\n"
                b'<xref ref-type="aff" rid="aff1">1</xref>\n'
                b"</contrib>\n"
                b'<aff id="aff1">\n'
                b"<institution>Swammerdam Institute for Life Sciences, Section of Molecular Cytology, van Leeuwenhoek Centre for Advanced Microscopy, University of Amsterdam, Science Park 904, 1098 XH, Amsterdam</institution>\n"
                b", \n"
                b"<country>The Netherlands</country>\n"
                b"</aff>\n"
                b"</contrib-group>\n"
            ),
            (
                b'<pub-date date-type="posted_date" publication-format="electronic">\n'
                b"<day>13</day>\n"
                b"<month>02</month>\n"
                b"<year>2023</year>\n"
                b"</pub-date>\n"
            ),
            b"<volume>12</volume>",
            b"<elocation-id>RP84364</elocation-id>",
            b"<history/>",
            (
                b"<pub-history>\n"
                b"<event>\n"
                b'<date date-type="preprint" iso-8601-date="2022-10-17">\n'
                b"<day>17</day>\n"
                b"<month>10</month>\n"
                b"<year>2022</year>\n"
                b"</date>\n"
                b'<self-uri content-type="preprint" xlink:href="https://doi.org/10.1101/2022.10.17.512253"/>\n'
                b"</event>\n"
                b"<event>\n"
                b'<date date-type="reviewed-preprint" iso-8601-date="2023-02-12">\n'
                b"<day>12</day>\n"
                b"<month>02</month>\n"
                b"<year>2023</year>\n"
                b"</date>\n"
                b'<self-uri content-type="reviewed-preprint" xlink:href="https://doi.org/10.7554/eLife.84364.1"/>\n'
                b"</event>\n"
                b"</pub-history>\n"
            ),
            (
                b"<permissions>\n"
                b'<license xlink:href="http://creativecommons.org/licenses/by/4.0/">\n'
                b"<license-p>\n"
                b'<ext-link ext-link-type="uri" xlink:href="http://creativecommons.org/licenses/by/4.0/"/>\n'
                b"</license-p>\n"
                b"</license>\n"
                b"</permissions>\n"
            ),
            (
                b"<abstract>\n"
                b"<p>An abstract.</p>\n"
                b"</abstract>\n"
                b"</article-meta>\n"
                b"</front>\n"
            ),
            (
                b'<sub-article id="sa0" article-type="editor-report">\n'
                b"<front-stub>\n"
                b'<article-id pub-id-type="doi">10.7554/eLife.84364.1.sa0</article-id>\n'
                b"<title-group>\n"
                b"<article-title>eLife assessment</article-title>\n"
                b"</title-group>\n"
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<name>\n"
                b"<surname>Eisen</surname>\n"
                b"<given-names>Michael B</given-names>\n"
                b"</name>\n"
                b"<aff>\n"
                b"<institution-wrap>\n"
                b"<institution>University of California</institution>\n"
                b", \n"
                b"</institution-wrap>\n"
                b"<addr-line>\n"
                b'<named-content content-type="city">Berkeley</named-content>\n'
                b"</addr-line>\n"
                b", \n"
                b"<country>United States</country>\n"
                b"</aff>\n"
                b"</contrib>\n"
                b"</contrib-group>\n"
                b"</front-stub>\n"
                b"</sub-article>\n"
            ),
            (
                b'<sub-article id="sa1" article-type="referee-report">\n'
                b"<front-stub>\n"
                b'<article-id pub-id-type="doi">10.7554/eLife.84364.1.sa1</article-id>\n'
                b"<title-group>\n"
                b"<article-title>Reviewer #1 (Public Review)</article-title>\n"
                b"</title-group>\n"
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<anonymous/>\n"
                b"</contrib>\n"
                b"</contrib-group>\n"
                b"</front-stub>\n"
                b"</sub-article>\n"
            ),
            (
                b'<sub-article id="sa2" article-type="referee-report">\n'
                b"<front-stub>\n"
                b'<article-id pub-id-type="doi">10.7554/eLife.84364.1.sa2</article-id>\n'
                b"<title-group>\n"
                b"<article-title>Reviewer #2 (Public Review)</article-title>\n"
                b"</title-group>\n"
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<anonymous/>\n"
                b"</contrib>\n"
                b"</contrib-group>\n"
                b"</front-stub>\n"
                b"</sub-article>\n"
            ),
            (
                b'<sub-article id="sa3" article-type="referee-report">\n'
                b"<front-stub>\n"
                b'<article-id pub-id-type="doi">10.7554/eLife.84364.1.sa3</article-id>\n'
                b"<title-group>\n"
                b"<article-title>Reviewer #3 (Public Review)</article-title>\n"
                b"</title-group>\n"
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<anonymous/>\n"
                b"</contrib>\n"
                b"</contrib-group>\n"
                b"</front-stub>\n"
                b"</sub-article>\n"
            ),
            (
                b'<sub-article id="sa4" article-type="author-comment">\n'
                b"<front-stub>\n"
                b'<article-id pub-id-type="doi">10.7554/eLife.84364.1.sa4</article-id>\n'
                b"<title-group>\n"
                b"<article-title>Author response</article-title>\n"
                b"</title-group>\n"
                b"<contrib-group>\n"
                b'<contrib contrib-type="author">\n'
                b"<name>\n"
                b"<surname>Mahlandt</surname>\n"
                b"<given-names>Eike K.</given-names>\n"
                b"</name>\n"
                b"</contrib>\n"
                b"</contrib-group>\n"
                b"</front-stub>\n"
                b"</sub-article>\n"
                b"</article>\n"
            ),
        ]
        result = preprint.preprint_xml(article, settings_mock)
        # print(bytes.decode(result))
        for fragment in expected_fragments:
            self.assertTrue(fragment in result, "%s not found in result" % fragment)
