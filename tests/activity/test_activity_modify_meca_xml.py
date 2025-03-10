# coding=utf-8

import copy
from collections import OrderedDict
from datetime import datetime
import importlib
import json
import os
import shutil
import time
import zipfile
import unittest
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
import docmaptools
from provider import utils
import activity.activity_ModifyMecaXml as activity_module
from activity.activity_ModifyMecaXml import (
    activity_ModifyMecaXml as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.ingest_meca_session_example()


SCIETY_DATA = {
    "https://sciety.org/evaluations/hypothesis:q48KAi1AEe-ua6f3BXQ_Lw/content": (
        b"<p><strong>%s</strong></p>\n"
        b"<p>The ....</p>\n" % b"Reviewer #2 (Public Review):"
    ),
    "https://sciety.org/evaluations/hypothesis:rAaVQC1AEe-pM4M18XukVQ/content": (
        b"<p><strong>%s</strong></p>\n"
        b"<p>The ....</p>\n" % b"Reviewer #1 (Public Review):"
    ),
    "https://sciety.org/evaluations/hypothesis:rIJAHi1AEe-JC-diPOFH3w/content": (
        b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"eLife assessment"
    ),
}


def mock_get_web_content(
    url=None,
):
    "return a content containing the response data based on the URL"
    if url and url in SCIETY_DATA:
        return SCIETY_DATA.get(url)
    # default
    return b"<p><strong>%s</strong></p>\n" b"<p>The ....</p>\n" % b"Title"


class TestModifyMecaXml(unittest.TestCase):
    def setUp(self):
        fake_logger = FakeLogger()
        self.activity = activity_object(settings_mock, fake_logger, None, None, None)
        # instantiate the session here so it can be wiped clean between test runs
        self.session = FakeSession(copy.copy(SESSION_DICT))
        self.session.store_value(
            "docmap_string", read_fixture("sample_docmap_for_95901.json")
        )

    def tearDown(self):
        TempDirectory.cleanup_all()
        # clean the temporary directory completely
        shutil.rmtree(self.activity.get_tmp_dir())
        # reset the session value
        self.session.store_value("docmap_string", None)
        # reload the module which had MagicMock applied to revert the mock
        importlib.reload(docmaptools)

    @patch("docmaptools.parse.get_web_content")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_storage_context,
        fake_get_web_content,
    ):
        directory = TempDirectory()

        fake_session.return_value = self.session

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_get_web_content.side_effect = mock_get_web_content
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)

        # assert statuses
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("xml_root"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("upload"),
            True,
        )

        # assertions on XML content
        with open(destination_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()

        self.assertTrue("<article" in xml_string)

        # assertions on article-id values
        self.assertTrue(
            '<article-id pub-id-type="publisher-id">95901</article-id>' in xml_string
        )
        self.assertTrue(
            '<article-id pub-id-type="doi">10.1101/2024.01.24.24301711</article-id>'
            not in xml_string
        )
        self.assertTrue(
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            in xml_string
        )
        self.assertTrue(
            (
                '<article-id pub-id-type="doi" specific-use="version">'
                "10.7554/eLife.95901.1"
                "</article-id>"
            )
            in xml_string
        )
        # assertions on article categories
        self.assertTrue("<subject>Cardiovascular Medicine</subject>" not in xml_string)
        self.assertTrue('<subj-group subj-group-type="heading">' in xml_string)
        self.assertTrue(
            "<subject>Epidemiology and Global Health</subject>" in xml_string
        )
        # assert volume tag
        self.assertTrue("<volume>13</volume>\n<elocation-id>" in xml_string)
        # assert elocation-id tag
        self.assertTrue("</volume>\n<elocation-id>RP95901</elocation-id>" in xml_string)
        # assert history tag
        self.assertTrue('<history>\n<date date-type="received">' not in xml_string)
        self.assertTrue(
            '<history>\n<date date-type="sent-for-review" iso-8601-date=' in xml_string
        )
        # assert pub-history
        self.assertTrue(
            (
                "<pub-history>\n"
                "<event>\n"
                "<event-desc>Preprint posted</event-desc>\n"
                '<date date-type="preprint" iso-8601-date="2024-01-24">\n'
                "<day>24</day>\n"
                "<month>01</month>\n"
                "<year>2024</year>\n"
                "</date>\n"
                '<self-uri content-type="preprint"'
                ' xlink:href="https://doi.org/10.1101/2024.01.24.24301711"/>\n'
                "</event>\n"
                "</pub-history>"
            )
            in xml_string
        )
        # assert permissions
        self.assertTrue(
            (
                "<permissions>\n"
                "<copyright-statement>© 2024, Liang et al</copyright-statement>\n"
                "<copyright-year>2024</copyright-year>\n"
                "<copyright-holder>Liang et al</copyright-holder>\n"
                "<ali:free_to_read/>\n"
                '<license xlink:href="https://creativecommons.org/licenses/by/4.0/">\n'
                "<ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref>\n"
                "<license-p>"
                "This article is distributed under the terms of the"
                ' <ext-link ext-link-type="uri"'
                ' xlink:href="https://creativecommons.org/licenses/by/4.0/">'
                "Creative Commons Attribution License"
                "</ext-link>"
                ", which permits unrestricted use and redistribution provided that the"
                " original author and source are credited."
                "</license-p>\n"
                "</license>"
            )
            in xml_string
        )
        # assert editor name
        self.assertTrue(
            (
                '<contrib-group content-type="section">\n'
                '<contrib contrib-type="editor">\n'
                "<name>\n"
                "<surname>Lamptey</surname>\n"
                "<given-names>Emmanuel</given-names>\n"
                "</name>\n"
                "<role>Reviewing Editor</role>\n"
                "<aff>\n"
                "<institution-wrap>\n"
                "<institution>KAAF University College</institution>\n"
                "</institution-wrap>\n"
                '<addr-line><named-content content-type="city">'
                "Buduburam"
                "</named-content></addr-line>\n"
                "<country>Ghana</country>\n"
                "</aff>\n"
                "</contrib>\n"
                '<contrib contrib-type="senior_editor">\n'
                "<name>\n"
                "<surname>Ajijola</surname>\n"
                "<given-names>Olujimi A</given-names>\n"
                "</name>\n"
                "<role>Senior Editor</role>\n"
                "<aff>\n"
                "<institution-wrap>\n"
                "<institution>University of California, Los Angeles</institution>\n"
                "</institution-wrap>\n"
                '<addr-line><named-content content-type="city">'
                "Los Angeles"
                "</named-content></addr-line>\n"
                "<country>United States of America</country>\n"
                "</aff>\n"
                "</contrib>\n"
                "</contrib-group>\n"
                "<author-notes>\n"
            )
            in xml_string
        )

    @patch("docmaptools.parse.get_web_content")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_minimal_docmap(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_get_web_content,
    ):
        "test if the docmap_string is missing some data"
        directory = TempDirectory()
        docmap_string = self.session.get_value("docmap_string")
        minimal_docmap = json.loads(docmap_string)
        del minimal_docmap["steps"]["_:b0"]["assertions"][0]["happened"]
        del minimal_docmap["steps"]["_:b1"]
        del minimal_docmap["steps"]["_:b2"]
        del minimal_docmap["steps"]["_:b3"]
        self.session.store_value("docmap_string", json.dumps(minimal_docmap))

        fake_session.return_value = self.session

        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_get_web_content.side_effect = mock_get_web_content
        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)

        # assert statuses
        self.assertEqual(
            self.activity.statuses.get("docmap_string"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("xml_root"),
            True,
        )
        self.assertEqual(
            self.activity.statuses.get("upload"),
            True,
        )

        # assertions on XML content
        with open(destination_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()

        self.assertTrue("<article" in xml_string)

        # assertions on article-id values
        self.assertTrue(
            '<article-id pub-id-type="doi">10.1101/2024.01.24.24301711</article-id>'
            not in xml_string
        )
        self.assertTrue(
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            in xml_string
        )
        self.assertTrue(
            (
                '<article-id pub-id-type="doi" specific-use="version">'
                "10.7554/eLife.95901.1"
                "</article-id>"
            )
            in xml_string
        )
        # assertions on article categories
        self.assertTrue("<subject>Cardiovascular Medicine</subject>" not in xml_string)
        self.assertTrue('<subj-group subj-group-type="heading">' not in xml_string)
        self.assertTrue(
            "<subject>Epidemiology and Global Health</subject>" not in xml_string
        )
        # assert volume tag
        self.assertTrue("<volume>13</volume>\n<elocation-id>" in xml_string)
        # assert elocation-id tag
        self.assertTrue("</volume>\n<elocation-id>RP95901</elocation-id>" in xml_string)
        # assert history tag
        self.assertTrue('<history>\n<date date-type="received">' not in xml_string)
        # assert pub-history
        self.assertTrue(
            (
                "<pub-history>\n"
                "<event>\n"
                "<event-desc>Preprint posted</event-desc>\n"
                '<date date-type="preprint" iso-8601-date="2024-01-24">\n'
                "<day>24</day>\n"
                "<month>01</month>\n"
                "<year>2024</year>\n"
                "</date>\n"
                '<self-uri content-type="preprint"'
                ' xlink:href="https://doi.org/10.1101/2024.01.24.24301711"/>\n'
                "</event>\n"
                "</pub-history>"
            )
            in xml_string
        )
        # assert permissions
        self.assertTrue(
            (
                "<permissions>\n"
                "<copyright-statement>© 2024, Liang et al</copyright-statement>\n"
                "<copyright-year>2024</copyright-year>\n"
                "<copyright-holder>Liang et al</copyright-holder>\n"
                "<ali:free_to_read/>\n"
                '<license xlink:href="https://creativecommons.org/licenses/by/4.0/">\n'
                "<ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref>\n"
                "<license-p>"
                "This article is distributed under the terms of the"
                ' <ext-link ext-link-type="uri"'
                ' xlink:href="https://creativecommons.org/licenses/by/4.0/">'
                "Creative Commons Attribution License"
                "</ext-link>"
                ", which permits unrestricted use and redistribution provided that the"
                " original author and source are credited."
                "</license-p>\n"
                "</license>"
            )
            in xml_string
        )
        # assert editor
        self.assertTrue('<contrib contrib-type="editor">' not in xml_string)

    @patch("docmaptools.parse.get_web_content")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_silent_correction(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_get_web_content,
    ):
        "test if the run_type is silent-correction"
        directory = TempDirectory()
        self.session.store_value("run_type", "silent-correction")
        fake_session.return_value = self.session

        fake_datetime.return_value = datetime.strptime(
            "2024-06-27 +0000", "%Y-%m-%d %z"
        )

        destination_path = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
            SESSION_DICT.get("article_xml_path"),
        )
        # create folders if they do not exist
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        resource_folder = os.path.join(
            directory.path,
            SESSION_DICT.get("expanded_folder"),
        )
        # create folders if they do not exist
        os.makedirs(resource_folder, exist_ok=True)
        # unzip the test fixture files
        zip_file_paths = helpers.unzip_fixture(meca_file_path, resource_folder)
        resources = [
            os.path.join(
                test_activity_data.ingest_meca_session_example().get("expanded_folder"),
                file_path,
            )
            for file_path in zip_file_paths
        ]
        fake_storage_context.return_value = FakeStorageContext(
            directory.path, resources, dest_folder=directory.path
        )
        fake_get_web_content.side_effect = mock_get_web_content
        # add XML to mirror typical silent-correction ingestion data
        xml_file_path = os.path.join(
            directory.path,
            test_activity_data.ingest_meca_session_example().get("expanded_folder"),
            "content/24301711.xml",
        )
        editor_xml = (
            '<contrib-group content-type="section">\n'
            '<contrib contrib-type="editor"></contrib>\n'
            '<contrib contrib-type="senior_editor"></contrib>\n'
            "</contrib-group>\n"
        )
        pub_history_xml = "<pub-history>\n<event>\n</event>\n</pub-history>"
        with open(xml_file_path, "r", encoding="utf-8") as open_file:
            xml_content = open_file.read()
        xml_content = xml_content.replace(
            "</contrib-group>\n<author-notes>",
            "</contrib-group>\n%s<author-notes>" % editor_xml,
        )
        xml_content = xml_content.replace(
            "</history>\n<permissions>",
            "</history>\n%s<permissions>" % pub_history_xml,
        )
        with open(xml_file_path, "w", encoding="utf-8") as open_file:
            open_file.write(xml_content)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        # assertions on XML content
        with open(destination_path, "r", encoding="utf-8") as open_file:
            xml_string = open_file.read()
        # assert pub-history
        self.assertTrue(
            (
                "<pub-history>\n"
                "<event>\n"
                "<event-desc>Preprint posted</event-desc>\n"
                '<date date-type="preprint" iso-8601-date="2024-01-24">\n'
                "<day>24</day>\n"
                "<month>01</month>\n"
                "<year>2024</year>\n"
                "</date>\n"
                '<self-uri content-type="preprint"'
                ' xlink:href="https://doi.org/10.1101/2024.01.24.24301711"/>\n'
                "</event>\n"
                "</pub-history>"
            )
            in xml_string
        )

        # assert editor XML
        self.assertTrue(
            (
                "</aff>\n"
                "</contrib-group>\n"
                '<contrib-group content-type="section">\n'
                '<contrib contrib-type="editor">\n'
                "<name>\n"
                "<surname>Lamptey</surname>\n"
                "<given-names>Emmanuel</given-names>\n"
                "</name>\n"
                "<role>Reviewing Editor</role>\n"
                "<aff>\n"
                "<institution-wrap>\n"
                "<institution>KAAF University College</institution>\n"
                "</institution-wrap>\n"
                '<addr-line><named-content content-type="city">'
                "Buduburam</named-content></addr-line>\n"
                "<country>Ghana</country>\n"
                "</aff>\n"
                "</contrib>\n"
                '<contrib contrib-type="senior_editor">\n'
                "<name>\n"
                "<surname>Ajijola</surname>\n"
                "<given-names>Olujimi A</given-names>\n"
                "</name>\n"
                "<role>Senior Editor</role>\n"
                "<aff>\n"
                "<institution-wrap>\n"
                "<institution>University of California, Los Angeles</institution>\n"
                "</institution-wrap>\n"
                '<addr-line><named-content content-type="city">'
                "Los Angeles</named-content></addr-line>\n"
                "<country>United States of America</country>\n"
                "</aff>\n"
                "</contrib>\n"
                "</contrib-group>\n"
            )
            in xml_string
        )


class TestClearArticleId(unittest.TestCase):
    "tests for clear_article_id()"

    def test_clear_article_id(self):
        "test removing article-id tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-id />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = "<article><front><article-meta /></front></article>"
        # invoke
        activity_module.clear_article_id(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyArticleId(unittest.TestCase):
    "tests for modify_article_id()"

    def test_modify_article_id(self):
        "test clearing and adding article-id tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-id />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        article_id = 95901
        doi = "10.7554/eLife.95901"
        version_doi = "10.7554/eLife.95901.1"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            '<article-id pub-id-type="publisher-id">95901</article-id>'
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            '<article-id pub-id-type="doi" specific-use="version">'
            "10.7554/eLife.95901.1"
            "</article-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_article_id(xml_root, article_id, doi, version_doi)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyElocationId(unittest.TestCase):
    "tests for modify_elocation_id()"

    def test_modify_elocation_id(self):
        "test setting existing elocatoin-id tag value"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id>1</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        elocation_id = "RP95901"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id>RP95901</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_elocation_id(xml_root, elocation_id)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_add_elocation_id(self):
        "test adding an elocation-id tag"
        xml_root = ElementTree.fromstring(
            "<article><front><article-meta /></front></article>"
        )
        elocation_id = "RP95901"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id>RP95901</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_elocation_id(xml_root, elocation_id)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_no_elocation_id(self):
        "test no elocation_id will remove the elocation-id tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<elocation-id>1</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        elocation_id = None
        expected = "<article><front><article-meta /></front></article>"
        # invoke
        activity_module.modify_elocation_id(xml_root, elocation_id)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyArticleCategories(unittest.TestCase):
    "tests for modify_article_categories()"

    def test_modify_article_categories(self):
        "test removing and adding subject tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="heading">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        display_channel = "Research Article"
        article_categories = ["Epidemiology and Global Health"]
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="display-channel">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            '<subj-group subj-group-type="heading">'
            "<subject>Epidemiology and Global Health</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_article_categories(
            xml_root, display_channel, article_categories
        )
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_add_article_categories(self):
        "test adding article-categories tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            '<article-id pub-id-type="doi" specific-use="version">'
            "10.7554/eLife.95901.1"
            "</article-id>"
            "<title-group>"
            "<article-title>Title</article-title>"
            "</title-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        display_channel = "Research Article"
        article_categories = ["Epidemiology and Global Health"]
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            '<article-id pub-id-type="doi">10.7554/eLife.95901</article-id>'
            '<article-id pub-id-type="doi" specific-use="version">'
            "10.7554/eLife.95901.1"
            "</article-id>"
            "<article-categories>"
            '<subj-group subj-group-type="display-channel">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            '<subj-group subj-group-type="heading">'
            "<subject>Epidemiology and Global Health</subject>"
            "</subj-group>"
            "</article-categories>"
            "<title-group>"
            "<article-title>Title</article-title>"
            "</title-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_article_categories(
            xml_root, display_channel, article_categories
        )
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_no_article_categories(self):
        "test no data will remove the article-categories tag"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<article-categories>"
            '<subj-group subj-group-type="heading">'
            "<subject>Research Article</subject>"
            "</subj-group>"
            "</article-categories>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = "<article><front><article-meta /></front></article>"
        # invoke
        activity_module.modify_article_categories(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestModifyHistory(unittest.TestCase):
    "tests for modify_history()"

    def test_modify_history(self):
        "test removing history and add history with a review date"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume>13</volume>"
            "<elocation-id>RP95901</elocation-id>"
            "<history />"
            "<permissions />"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        review_date_struct = time.strptime("2024-01-24 +0000", "%Y-%m-%d %z")
        identifier = "10.7554/eLife.95901.1"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<volume>13</volume>"
            "<elocation-id>RP95901</elocation-id>"
            "<history>"
            '<date date-type="sent-for-review" iso-8601-date="2024-01-24">'
            "<day>24</day>"
            "<month>01</month>"
            "<year>2024</year>"
            "</date>"
            "</history>"
            "<permissions />"
            "</article-meta>"
            "</front></article>"
        )
        # invoke
        activity_module.modify_history(xml_root, review_date_struct, identifier)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestClearPubHistory(unittest.TestCase):
    "test for clear_pub_history()"

    def test_clear_pub_history(self):
        "test removing pub-history tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<pub-history><event /></pub-history>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = "<article>" "<front>" "<article-meta />" "</front>" "</article>"
        # invoke
        activity_module.clear_pub_history(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


class TestClearEditors(unittest.TestCase):
    "test for clear_editors()"

    def test_clear_editors(self):
        "test removing contrib-group tags holding editor contrib tags"
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<contrib-group>"
            '<contrib contrib-type="author" />'
            "</contrib-group>"
            '<contrib-group content-type="section">'
            '<contrib contrib-type="editor">'
            "<name>"
            "<surname>Editor</surname>"
            "</name>"
            "</contrib>"
            "</contrib-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<contrib-group>"
            '<contrib contrib-type="author" />'
            "</contrib-group>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.clear_editors(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)
