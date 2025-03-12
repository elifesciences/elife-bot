# coding=utf-8

import copy
from datetime import datetime
import importlib
import json
import os
import shutil
import unittest
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
import docmaptools
from provider import utils
import activity.activity_ModifyMecaPublishedXml as activity_module
from activity.activity_ModifyMecaPublishedXml import (
    activity_ModifyMecaPublishedXml as activity_object,
)
from tests import read_fixture
from tests.activity.classes_mock import (
    FakeLogger,
    FakeSession,
    FakeStorageContext,
)
from tests.activity import helpers, settings_mock, test_activity_data


SESSION_DICT = test_activity_data.post_preprint_publication_session_example()

PUB_DATE_XML = (
    '<pub-date date-type="original-publication" iso-8601-date="2024-06-19">'
    "<day>19</day><month>06</month><year>2024</year>"
    "</pub-date>"
    '<pub-date date-type="update" iso-8601-date="2024-08-14">'
    "<day>14</day><month>08</month><year>2024</year>"
    "</pub-date>"
)


class TestModifyMecaPublishedXml(unittest.TestCase):
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

    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_storage_context,
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

        # assert pub-date year tag
        self.assertTrue(
            '<pub-date pub-type="epub"><year>2024</year></pub-date>' not in xml_string
        )

        # assert volume tag
        self.assertTrue("<volume>13</volume>\n<elocation-id>" in xml_string)

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

    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_minimal_docmap(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
    ):
        "test if the docmap_string is missing some data"
        directory = TempDirectory()
        docmap_string = self.session.get_value("docmap_string")
        minimal_docmap = json.loads(docmap_string)
        del minimal_docmap["steps"]["_:b1"]
        del minimal_docmap["steps"]["_:b2"]
        del minimal_docmap["steps"]["_:b3"]["assertions"][0]["happened"]
        del minimal_docmap["steps"]["_:b4"]
        del minimal_docmap["steps"]["_:b5"]
        del minimal_docmap["steps"]["_:b6"]
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

        # assert volume tag
        self.assertTrue("<volume>13</volume>\n<elocation-id>" in xml_string)

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


class TestClearYearOnlyPubDate(unittest.TestCase):
    "tests for clear_year_only_pub_date()"

    def test_clear_year_only_pub_date(self):
        "test removing the particular pub-date tag"
        bad_pub_date_xml = '<pub-date pub-type="epub"><year>2024</year></pub-date>'
        good_pub_date_xml = PUB_DATE_XML

        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "%s%s"
            "</article-meta>"
            "</front>"
            "</article>" % (bad_pub_date_xml, good_pub_date_xml)
        )
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "%s"
            "</article-meta>"
            "</front>"
            "</article>" % good_pub_date_xml
        )
        # invoke
        activity_module.clear_year_only_pub_date(xml_root)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)


HISTORY_DATA = [
    {
        "type": "preprint",
        "date": "2024-01-24",
        "doi": "10.1101/2024.01.24.24301711",
        "url": "https://www.medrxiv.org/content/10.1101/2024.01.24.24301711v1",
        "versionIdentifier": "1",
        "published": "2024-01-24",
        "content": [
            {
                "type": "computer-file",
                "url": "s3://prod-elife-epp-meca/95901-v1-meca.zip",
            }
        ],
    },
    {
        "type": "reviewed-preprint",
        "date": "2024-06-19T14:00:00+00:00",
        "identifier": "95901",
        "doi": "10.7554/eLife.95901.1",
        "versionIdentifier": "1",
        "license": "http://creativecommons.org/licenses/by/4.0/",
        "published": "2024-06-19T14:00:00+00:00",
        "partOf": {
            "type": "manuscript",
            "doi": "10.7554/eLife.95901",
            "identifier": "95901",
            "subjectDisciplines": ["Epidemiology and Global Health"],
            "published": "2024-06-19T14:00:00+00:00",
            "volumeIdentifier": "13",
            "electronicArticleIdentifier": "RP95901",
            "complement": [],
        },
    },
    {
        "type": "reviewed-preprint",
        "date": "2024-08-14T14:00:00+00:00",
        "identifier": "95901",
        "doi": "10.7554/eLife.95901.2",
        "versionIdentifier": "2",
        "license": "http://creativecommons.org/licenses/by/4.0/",
        "published": "2024-08-14T14:00:00+00:00",
        "partOf": {
            "type": "manuscript",
            "doi": "10.7554/eLife.95901",
            "identifier": "95901",
            "subjectDisciplines": ["Epidemiology and Global Health"],
            "published": "2024-06-19T14:00:00+00:00",
            "volumeIdentifier": "13",
            "electronicArticleIdentifier": "RP95901",
            "complement": [],
        },
    },
]


class TestModifyPubDate(unittest.TestCase):
    "tests for modify_pub_date()"

    def test_modify_pub_date(self):
        "test clearing and adding article-id tags"
        xml_root = ElementTree.fromstring(
            "<article><front><article-meta><volume>13</volume></article-meta></front></article>"
        )
        doi = "10.7554/eLife.95901"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "%s"
            "<volume>13</volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        ) % PUB_DATE_XML
        # invoke
        activity_module.modify_pub_date(xml_root, HISTORY_DATA, doi)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_three_versions(self):
        "test more than two versions will output only two pub-date tags"
        extended_history_data = copy.copy(HISTORY_DATA)
        extended_history_data.append(
            {
                "type": "reviewed-preprint",
                "date": "2024-09-15T14:00:00+00:00",
                "identifier": "95901",
                "doi": "10.7554/eLife.95901.3",
                "versionIdentifier": "3",
                "license": "http://creativecommons.org/licenses/by/4.0/",
                "published": "2024-09-15T14:00:00+00:00",
                "partOf": {
                    "type": "manuscript",
                    "doi": "10.7554/eLife.95901",
                    "identifier": "95901",
                    "subjectDisciplines": ["Epidemiology and Global Health"],
                    "published": "2024-06-19T14:00:00+00:00",
                    "volumeIdentifier": "13",
                    "electronicArticleIdentifier": "RP95901",
                    "complement": [],
                },
            }
        )
        xml_root = ElementTree.fromstring(
            "<article><front><article-meta><volume>13</volume></article-meta></front></article>"
        )
        doi = "10.7554/eLife.95901"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            '<pub-date date-type="original-publication" iso-8601-date="2024-06-19">'
            "<day>19</day><month>06</month><year>2024</year>"
            "</pub-date>"
            '<pub-date date-type="update" iso-8601-date="2024-09-15">'
            "<day>15</day><month>09</month><year>2024</year>"
            "</pub-date>"
            "<volume>13</volume>"
            "</article-meta>"
            "</front>"
            "</article>"
        )
        # invoke
        activity_module.modify_pub_date(xml_root, extended_history_data, doi)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(xml_string, expected)

    def test_insert_after_pub_date(self):
        "test adding pub-date tags after existing pub-date tag"
        keep_pub_date_tag = (
            '<pub-date date-type="epub" iso-8601-date="2024-06-19">'
            "<day>19</day><month>06</month><year>2024</year>"
            "</pub-date>"
        )
        remove_pub_date_tag = (
            '<pub-date date-type="original-publication" iso-8601-date="2024-06-19">'
            "<day>19</day><month>06</month><year>2024</year>"
            "</pub-date>"
        )
        xml_root = ElementTree.fromstring(
            "<article>"
            "<front>"
            "<article-meta>"
            "<author-notes />"
            "%s%s"
            "<elocation-id>RP95901</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>" % (keep_pub_date_tag, remove_pub_date_tag)
        )
        doi = "10.7554/eLife.95901"
        expected = (
            "<article>"
            "<front>"
            "<article-meta>"
            "<author-notes />"
            "%s"
            "%s"
            "<elocation-id>RP95901</elocation-id>"
            "</article-meta>"
            "</front>"
            "</article>"
        ) % (keep_pub_date_tag, PUB_DATE_XML)
        # invoke
        activity_module.modify_pub_date(xml_root, HISTORY_DATA, doi)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")

        self.assertEqual(xml_string, expected)
