# coding=utf-8

import os
import time
import unittest
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from mock import patch
from testfixtures import TempDirectory
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
from tests.activity.classes_mock import FakeLogger, FakeResponse, FakeStorageContext
from provider import cleaner, download_helper, preprint


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
    article.abstract = "<p>An abstract.</p>"
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
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
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
        self.assertEqual(len(article.contributors[0].affiliations), 1)
        self.assertEqual(len(article.ref_list), 0)
        # review_articles
        self.assertEqual(len(article.review_articles), 5)

        # assertions on the review articles
        self.assertEqual(article.review_articles[0].article_type, "editor-report")
        self.assertEqual(article.review_articles[0].doi, "10.7554/eLife.84364.2.sa4")
        self.assertEqual(article.review_articles[0].id, "sa4")
        self.assertEqual(article.review_articles[0].title, "eLife assessment")
        self.assertEqual(len(article.review_articles[0].contributors), 1)
        self.assertEqual(article.review_articles[0].contributors[0].surname, "Eisen")

        self.assertEqual(len(article.related_articles), 0)

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

        # self.assertTrue(False)

    @patch.object(cleaner, "sub_article_data")
    def test_specific_version(self, fake_sub_article_data):
        "test building an Article for a specific version"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        version = 1
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
        article = preprint.build_article(
            article_id, docmap_string, article_xml_path, version
        )
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

    @patch.object(cleaner, "version_doi_from_docmap")
    @patch.object(cleaner, "sub_article_data")
    def test_no_posted_date(self, fake_sub_article_data, fake_version_doi):
        "test if an exception is raised due to no poasted date"
        fake_version_doi.return_value = "10.7554/eLife.84364.2"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        # remove the date from the docmap fixture
        docmap_string = docmap_string.replace(
            b'"published": "2023-06-14T14:00:00+00:00",', b""
        )
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
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
            preprint.build_article(None, None, None)

    @patch.object(cleaner, "version_doi_from_docmap")
    def test_incorrect_version_doi(self, fake_version_doi):
        fake_version_doi.return_value = "10.999999/unwanted.doi"
        with self.assertRaises(preprint.PreprintArticleException) as test_exception:
            preprint.build_article(None, None, None)


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

    @patch.object(cleaner, "sub_article_data")
    def test_article_preprint_xml(self, fake_sub_article_data):
        "test building an article object then generate the article XML"
        fake_sub_article_data.return_value = sub_article_data_fixture()
        article_id = "84364"
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
        article = preprint.build_article(article_id, docmap_string, article_xml_path)
        result = preprint.preprint_xml(article, settings_mock)
        # print(bytes.decode(result))
        # assertions
        self.assertTrue(
            b'<self-uri content-type="preprint" '
            b'xlink:href="https://doi.org/10.1101/2022.10.17.512253"/>' in result
        )
        self.assertTrue(
            b'<aff id="aff1">\n<institution>Swammerdam Institute for Life Sciences, '
            b"Section of Molecular Cytology, van Leeuwenhoek Centre for "
            b"Advanced Microscopy, University of Amsterdam, Science Park 904</institution>"
            b"\n, \n<country>The Netherlands</country>\n</aff>" in result
        )


class TestDownloadOriginalPreprintXml(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch.object(download_helper, "storage_context")
    def test_download_automated_preprint_xml(self, fake_download_storage_context):
        directory = TempDirectory()
        article_id = 93405
        version = 1
        file_name = "article-source.xml"
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", [file_name]
        )
        result = preprint.download_original_preprint_xml(
            settings_mock, directory.path, article_id, version
        )
        self.assertEqual(result.rsplit(os.sep, 1)[-1], file_name)
        self.assertTrue(file_name in os.listdir(directory.path))


class TestBuildPreprintArticle(unittest.TestCase):
    "tests for preprint.build_preprint_article()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.get")
    @patch.object(download_helper, "storage_context")
    def test_build_preprint_article(self, fake_download_storage_context, fake_get):
        "build an Article object from biorXiv XML and docmap string data"
        fake_logger = FakeLogger()
        file_name = "article-source.xml"
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", [file_name]
        )
        article_id = 93405
        version = 1
        docmap_string = read_fixture("sample_docmap_for_84364.json")
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)
        # invoke
        result = preprint.build_preprint_article(
            article_id,
            version,
            docmap_string,
            article_xml_path,
            fake_logger,
        )
        # assert
        self.assertTrue(isinstance(result, Article))

    @patch.object(preprint, "build_article")
    @patch.object(download_helper, "storage_context")
    def test_build_article_exception(
        self, fake_download_storage_context, fake_build_article
    ):
        "test an exception raised building the Article object"
        directory = TempDirectory()
        fake_logger = FakeLogger()
        exception_message = "An exception"
        fake_build_article.side_effect = preprint.PreprintArticleException(
            exception_message
        )
        file_name = "article-source.xml"
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", [file_name]
        )
        article_id = 93405
        version = 1
        docmap_string = read_fixture("sample_docmap_for_84364.json")

        # invoke
        with self.assertRaises(preprint.PreprintArticleException):
            preprint.build_preprint_article(
                article_id,
                version,
                docmap_string,
                directory.path,
                fake_logger,
            )
        # assert
        self.assertEqual(fake_logger.logexception, exception_message)


class TestGeneratePreprintXml(unittest.TestCase):
    "tests for preprint.generate_preprint_xml()"

    def setUp(self):
        # reduce the sleep time to speed up test runs
        cleaner.DOCMAP_SLEEP_SECONDS = 0.001
        cleaner.DOCMAP_RETRY = 2

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("requests.get")
    @patch.object(download_helper, "storage_context")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_generate_preprint_xml(
        self, fake_get_docmap_string, fake_download_storage_context, fake_get
    ):
        "test PreprintArticleException exception raised generating preprint XML"
        directory = TempDirectory()
        fake_logger = FakeLogger()

        # set and create testing directories
        directories = {
            "TEMP_DIR": os.path.join(directory.path, "tmp_dir"),
            "INPUT_DIR": os.path.join(directory.path, "input_dir"),
        }
        for value in directories.values():
            os.mkdir(value)

        article_id = 84364
        version = 2
        fake_download_storage_context.return_value = FakeStorageContext(
            "tests/files_source/epp", ["article-source.xml"]
        )
        fake_get_docmap_string.return_value = read_fixture(
            "sample_docmap_for_84364.json"
        )
        caller_name = "ScheduleCrossrefPreprint"
        sample_html = b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"
        fake_get.return_value = FakeResponse(200, content=sample_html)

        # invoke
        xml_file_path = preprint.generate_preprint_xml(
            settings_mock,
            article_id,
            version,
            caller_name,
            directories,
            fake_logger,
        )

        # assert
        self.assertTrue(xml_file_path.endswith("input_dir/elife-preprint-84364-v2.xml"))

    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_docmap_exception(self, fake_get_docmap_string):
        "test PreprintArticleException exception raised when getting a docmap"
        fake_logger = FakeLogger()
        article_id = 84364
        version = 2
        directories = {}
        caller_name = "ScheduleCrossrefPreprint"
        exception_message = "An exception"
        fake_get_docmap_string.side_effect = preprint.PreprintArticleException(
            exception_message
        )

        # invoke
        with self.assertRaises(preprint.PreprintArticleException):
            preprint.generate_preprint_xml(
                settings_mock,
                article_id,
                version,
                caller_name,
                directories,
                fake_logger,
            )
        # assert
        self.assertEqual(
            fake_logger.logexception,
            (
                "%s, exception raised to get docmap_string"
                " using retries for article_id %s version %s"
            )
            % (caller_name, article_id, version),
        )

    @patch.object(preprint, "download_original_preprint_xml")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_download_xml_exception(self, fake_get_docmap_string, fake_download):
        "test PreprintArticleException exception raised when downloading original prepring XML"
        fake_logger = FakeLogger()
        article_id = 84364
        version = 2
        directories = {}
        caller_name = "ScheduleCrossrefPreprint"
        exception_message = "An exception"
        fake_get_docmap_string.return_value = True
        fake_download.side_effect = preprint.PreprintArticleException(exception_message)

        # invoke
        with self.assertRaises(preprint.PreprintArticleException):
            preprint.generate_preprint_xml(
                settings_mock,
                article_id,
                version,
                caller_name,
                directories,
                fake_logger,
            )
        # assert
        self.assertEqual(
            fake_logger.logexception,
            (
                "%s, exception getting preprint server XML from the bucket"
                " for article_id %s version %s"
            )
            % (caller_name, article_id, version),
        )

    @patch.object(preprint, "download_original_preprint_xml")
    @patch.object(preprint, "build_preprint_article")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_build_article_exception(
        self, fake_get_docmap_string, fake_build_article, fake_download
    ):
        "test PreprintArticleException is raised when generating an article"
        fake_logger = FakeLogger()
        article_id = 84364
        version = 2
        directories = {}
        caller_name = "ScheduleCrossrefPreprint"
        fake_get_docmap_string.return_value = True
        fake_download.return_value = True
        exception_message = "An exception"
        fake_build_article.side_effect = preprint.PreprintArticleException(
            exception_message
        )

        # invoke
        with self.assertRaises(preprint.PreprintArticleException):
            preprint.generate_preprint_xml(
                settings_mock,
                article_id,
                version,
                caller_name,
                directories,
                fake_logger,
            )
        # assert
        self.assertEqual(
            fake_logger.logexception,
            (
                "%s, exception raised when building the article object"
                " for article_id %s version %s"
            )
            % (caller_name, article_id, version),
        )

    @patch.object(preprint, "copy_ref_list_xml")
    @patch.object(preprint, "download_original_preprint_xml")
    @patch.object(preprint, "build_preprint_article")
    @patch.object(cleaner, "get_docmap_string_with_retry")
    def test_copy_ref_list_exception(
        self, fake_get_docmap_string, fake_build_article, fake_download, fake_copy
    ):
        "test PreprintArticleException is raised when generating an article"
        directory = TempDirectory()
        fake_logger = FakeLogger()
        article_id = 84364
        version = 2
        directories = {"INPUT_DIR": directory.path}
        caller_name = "ScheduleCrossrefPreprint"
        fake_get_docmap_string.return_value = True
        fake_download.return_value = True
        fake_build_article.return_value = Article()
        exception_message = "An exception"
        fake_copy.side_effect = Exception(exception_message)

        # invoke
        preprint.generate_preprint_xml(
            settings_mock,
            article_id,
            version,
            caller_name,
            directories,
            fake_logger,
        )
        # assert
        self.assertEqual(
            fake_logger.logexception,
            (
                "%s, exception raised when copying ref-list XML"
                " for article_id %s version %s"
            )
            % (caller_name, article_id, version),
        )


class TestCopyRefListXml(unittest.TestCase):
    "tests for preprint.copy_ref_list_xml()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_copy_ref_list_xml(self):
        "simple copy of ref-list XML"
        article_xml_path = (
            "tests/files_source/epp/automation/84364/v2/article-source.xml"
        )
        xml_string = "<root/>"
        result = preprint.copy_ref_list_xml(article_xml_path, xml_string)
        self.assertTrue(b"<back>" in result)
        self.assertTrue(b"<ref-list>" in result)

    def test_no_ref_list_to_copy(self):
        "no ref-list in the article XML file"
        directory = TempDirectory()
        article_xml_path = os.path.join(directory.path, "article-source.xml")
        with open(article_xml_path, "wb") as open_file:
            open_file.write(b"<article/>")
        xml_string = "<root/>"
        result = preprint.copy_ref_list_xml(article_xml_path, xml_string)
        self.assertEqual(result, b'<?xml version="1.0" encoding="utf-8"?>\n<root/>\n')


class TestExpandedFolderBucketResource(unittest.TestCase):
    "tests for preprint.expanded_folder_bucket_resource()"

    def test_expanded_folder_bucket_resource(self):
        "test constructing the path to a bucket expanded folder"
        bucket_name = (
            settings_mock.publishing_buckets_prefix + settings_mock.expanded_bucket
        )
        folder_name = "preprint.84364.2"
        expected = "s3://%s/%s" % (bucket_name, folder_name)
        result = preprint.expanded_folder_bucket_resource(
            settings_mock, bucket_name, folder_name
        )
        self.assertEqual(result, expected)


class TestFindXmlFilenameInExpandedFolder(unittest.TestCase):
    "tests for preprint.find_xml_filename_in_expanded_folder()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("provider.preprint.storage_context")
    def test_find_xml_filename_in_expanded_folder(self, fake_preprint_storage_context):
        "test finding the preprint XML file in the bucket expanded folder"
        directory = TempDirectory()
        file_name = "elife-preprint-84364-v2.xml"
        fake_preprint_storage_context.return_value = FakeStorageContext(
            resources=[file_name], dest_folder=directory.path
        )
        bucket_resource = "s3://%s/%s/%s" % (
            (settings_mock.publishing_buckets_prefix + settings_mock.expanded_bucket),
            "preprint.84364.2",
            "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
        )
        result = preprint.find_xml_filename_in_expanded_folder(
            settings_mock, bucket_resource
        )
        self.assertEqual(result, file_name)


class TestDownloadFromExpandedFolder(unittest.TestCase):
    def tearDown(self):
        TempDirectory.cleanup_all()

    @patch("provider.preprint.storage_context")
    def test_download_from_expanded_folder(self, fake_preprint_storage_context):
        "test downloading preprint XML file from the bucket expanded folder"
        directory = TempDirectory()
        file_name = "elife-preprint-84364-v2.xml"
        fake_preprint_storage_context.return_value = FakeStorageContext(
            resources=[file_name], dest_folder=directory.path
        )
        bucket_resource = "s3://%s/%s/%s" % (
            (settings_mock.publishing_buckets_prefix + settings_mock.expanded_bucket),
            "preprint.84364.2",
            "1ee54f9a-cb28-4c8e-8232-4b317cf4beda",
        )
        directories = {"INPUT_DIR": directory.path}
        caller_name = "ScheduleCrossrefPreprint"
        logger = FakeLogger()
        # invoke
        result = preprint.download_from_expanded_folder(
            settings_mock, directories, file_name, bucket_resource, caller_name, logger
        )
        # assert
        self.assertTrue(result.endswith(file_name))
        self.assertEqual(os.listdir(directory.path)[0], file_name)


class TestGetPreprintPdfUrl(unittest.TestCase):
    "tests for get_preprint_pdf_url()"

    def setUp(self):
        article_id = 95901
        version = 1
        self.endpoint_url = settings_mock.reviewed_preprint_api_endpoint.format(
            article_id=article_id, version=version
        )
        self.caller_name = "FindPreprintPDF"
        self.user_agent = "user-agent"

    @patch("requests.get")
    def test_200(self, fake_get):
        "test status code 200"
        pdf_url = "https://example.org/article.pdf"
        fake_get.return_value = FakeResponse(
            200,
            response_json={"pdf": pdf_url},
        )
        # invoke
        result = preprint.get_preprint_pdf_url(
            self.endpoint_url, self.caller_name, self.user_agent
        )
        # assert
        self.assertEqual(result, pdf_url)

    @patch("requests.get")
    def test_404(self, fake_get):
        "test status code 404"
        fake_get.return_value = FakeResponse(
            404,
            response_json={"title": "not found"},
        )
        # invoke
        result = preprint.get_preprint_pdf_url(
            self.endpoint_url, self.caller_name, self.user_agent
        )
        # assert
        self.assertEqual(result, None)

    @patch("requests.get")
    def test_500(self, fake_get):
        "test status code 500"
        fake_get.return_value = FakeResponse(500)
        # invoke and assert
        with self.assertRaises(RuntimeError):
            preprint.get_preprint_pdf_url(
                self.endpoint_url, self.caller_name, self.user_agent
            )


class TestClearPdfSelfUri(unittest.TestCase):
    "tests for clear_pdf_self_uri()"

    def test_clear_pdf_self_uri(self):
        "test removing pdf self-uri tags"
        xml_string = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            "<front><article-meta>"
            "<permissions />"
            '<self-uri xlink:href="https://example.org" />'
            '<self-uri xlink:href="24301711.pdf" content-type="pdf" xlink:role="full-text" />'
            "<related-article />"
            "</article-meta></front>"
            "</article>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        expected = (
            b'<article xmlns:xlink="http://www.w3.org/1999/xlink">'
            b"<front><article-meta>"
            b"<permissions />"
            b'<self-uri xlink:href="https://example.org" />'
            b"<related-article />"
            b"</article-meta></front>"
            b"</article>"
        )
        # invoke
        preprint.clear_pdf_self_uri(xml_root)
        # assert
        self.assertEqual(ElementTree.tostring(xml_root), expected)


class TestSetPdfSelfUri(unittest.TestCase):
    "tests for set_pdf_self_uri()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_set_pdf_self_uri(self):
        "test replacing an existing self-uri tag"
        directory = TempDirectory()
        xml_header = (
            '<?xml version="1.0" ?>'
            '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96)'
            ' Journal Archiving and Interchange DTD v1.3 20210610//EN"'
            '  "JATS-archivearticle1-mathml3.dtd">'
        )
        article_open_tag = (
            '<article xmlns:xlink="http://www.w3.org/1999/xlink"'
            ' article-type="research-article" dtd-version="1.3" xml:lang="en">'
        )
        xml_string = (
            "%s%s"
            "<front><article-meta>"
            "<pub-history/>"
            "<permissions/>"
            '<self-uri xlink:href="24301711.pdf" content-type="pdf" xlink:role="full-text"/>'
            "<related-article/>"
            "</article-meta></front></article>" % (xml_header, article_open_tag)
        )
        xml_file_name = "article.xml"
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        pdf_file_name = "elife-preprint-95901-v1.pdf"
        identifier = "10.7554/eLife.95901.1"
        expected = (
            "%s%s"
            "<front><article-meta>"
            "<pub-history/>"
            "<permissions/>"
            '<self-uri content-type="pdf" xlink:href="elife-preprint-95901-v1.pdf"/>\n'
            "<related-article/>"
            "</article-meta></front></article>" % (xml_header, article_open_tag)
        )
        # invoke
        preprint.set_pdf_self_uri(xml_file_path, pdf_file_name, identifier)
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        self.assertEqual(xml_content, expected)

    def test_add_new_pdf_self_uri(self):
        "test adding a self-uri tag"
        directory = TempDirectory()
        xml_header = (
            '<?xml version="1.0" ?>'
            '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96)'
            ' Journal Archiving and Interchange DTD v1.3 20210610//EN"'
            '  "JATS-archivearticle1-mathml3.dtd">'
        )
        xml_string = (
            "%s"
            '<article article-type="research-article" dtd-version="1.3" xml:lang="en">'
            "<front><article-meta>"
            "<pub-history/>"
            "<permissions/>"
            "<related-article/>"
            "</article-meta></front></article>" % xml_header
        )
        xml_file_name = "article.xml"
        xml_file_path = os.path.join(directory.path, xml_file_name)
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_string)
        pdf_file_name = "elife-preprint-95901-v1.pdf"
        identifier = "10.7554/eLife.95901.1"
        expected = (
            "%s"
            '<article xmlns:xlink="http://www.w3.org/1999/xlink"'
            ' article-type="research-article" dtd-version="1.3" xml:lang="en">'
            "<front><article-meta>"
            "<pub-history/>"
            "<permissions/>"
            '<self-uri content-type="pdf" xlink:href="elife-preprint-95901-v1.pdf"/>\n'
            "<related-article/>"
            "</article-meta></front></article>" % xml_header
        )
        # invoke
        preprint.set_pdf_self_uri(xml_file_path, pdf_file_name, identifier)
        # assert
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        self.assertEqual(xml_content, expected)
