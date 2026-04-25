# coding=utf-8

import copy
from datetime import datetime
import importlib
import json
import os
import shutil
import time
import unittest
import zipfile
from xml.etree import ElementTree
from mock import patch
from testfixtures import TempDirectory
import docmaptools
from provider import bigquery, utils
import activity.activity_ModifyMecaXml as activity_module
from activity.activity_ModifyMecaXml import (
    activity_ModifyMecaXml as activity_object,
)
from tests import bigquery_test_data, read_fixture
from tests.classes_mock import (
    FakeBigQueryClient,
    FakeBigQueryRowIterator,
)
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

    @patch.object(bigquery, "get_author_data")
    @patch.object(bigquery, "get_funding_data")
    @patch.object(bigquery, "get_client")
    @patch("docmaptools.parse.get_web_content")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_do_activity(
        self,
        fake_session,
        fake_storage_context,
        fake_get_web_content,
        fake_bigquery_get_client,
        fake_funding_data,
        fake_author_data,
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            [bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT]
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        funding_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        fake_funding_data.return_value = funding_data_rows

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        fake_author_data.return_value = author_data_rows

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

        # assert data availability statement
        self.assertTrue(
            (
                '<sec id="das" sec-type="data-availability">\n'
                "<p>Sequencing data (fastq) is available in the Sequence Read Archive (SRA)"
                " with the BioProject identification PRJNA934938. Scripts used for ChIP-seq,"
                " RNA-seq, and VSG-seq analysis are available at"
                " https://github.com/cestari-lab/lab_scripts. A specific pipeline was developed"
                " for clonal VSG-seq analysis, available at"
                " https://github.com/cestari-lab/VSG-Bar-seq.</p>\n"
                "</sec>\n"
            )
            in xml_string
        )

        self.assertTrue(
            (
                '<ref id="dataref1">\n'
                '<element-citation publication-type="data" specific-use="generated">\n'
                '<person-group person-group-type="author">\n'
                "<collab>Touray AO, Rajesh R, Isebe I, Sternlieb T,"
                " Loock M, Kutova O, Cestari I</collab>\n"
                "</person-group>\n"
                "<article-title>Trypanosoma brucei brucei strain:Lister 427 DNA or"
                " RNA sequencing</article-title>\n"
                "<source>SRA Bioproject PRJNA934938</source>\n"
                '<year iso-8601-date="2023">2023</year>\n'
                '<ext-link ext-link-type="uri"'
                ' xlink:href="https://dataview.ncbi.nlm.nih.gov/object/PRJNA934938">\n'
                "</ext-link>\n"
                "</element-citation>\n"
                "</ref>\n"
                '<ref id="dataref2">\n'
                '<element-citation publication-type="data" specific-use="analyzed">\n'
                '<person-group person-group-type="author">\n'
                "<collab>B. Akiyoshi, K. Gull</collab>\n"
                "</person-group>\n"
                "<article-title>Trypanosoma brucei KKT2 ChIP</article-title>\n"
                "<source>SRA, accession numbers SRR1023669 and SRX372731</source>\n"
                '<year iso-8601-date="2014">2014</year>\n'
                '<ext-link ext-link-type="uri"'
                ' xlink:href="https://www.ncbi.nlm.nih.gov/sra/?term=SRP031518">\n'
                "</ext-link>\n"
                "</element-citation>\n"
                "</ref>\n"
                "</ref-list>\n"
            )
            in xml_string
        )

    @patch.object(bigquery, "get_author_data")
    @patch.object(bigquery, "get_funding_data")
    @patch.object(bigquery, "get_client")
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
        fake_bigquery_get_client,
        fake_funding_data,
        fake_author_data,
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            [bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT]
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        funding_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        fake_funding_data.return_value = funding_data_rows

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        fake_author_data.return_value = author_data_rows

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

        # assert funding
        self.assertTrue(
            (
                "<funding-group>\n"
                '<award-group id="par-1">\n'
                "<funding-source>\n"
                "<institution-wrap>\n"
                '<institution-id institution-id-type="FundRef">'
                "http://dx.doi.org/10.13039/100000050"
                "</institution-id>\n"
                "<institution>"
                "HHS | NIH | National Heart, Lung, and Blood Institute (NHLBI)"
                "</institution>\n"
                "</institution-wrap>\n"
                "</funding-source>\n"
                "<award-id>R01HL126066</award-id>\n"
                "<principal-award-recipient>Igor  Kramnik</principal-award-recipient>\n"
                "</award-group>\n"
            )
            in xml_string
        )

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

    @patch.object(bigquery, "get_client")
    @patch("docmaptools.parse.get_web_content")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_no_bigquery_data_availability_data(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_get_web_content,
        fake_bigquery_get_client,
    ):
        "test if no data availability data is returned from BigQuery"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator([])
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertTrue(
            (
                "ModifyMecaXml, no data availability data from BigQuery"
                " for article_id 95901, version 1"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(bigquery, "get_author_data")
    @patch.object(activity_module, "add_data_availability")
    @patch.object(bigquery, "get_client")
    @patch("docmaptools.parse.get_web_content")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_data_availability_exception(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_get_web_content,
        fake_bigquery_get_client,
        fake_add_data_availability,
        fake_author_data,
    ):
        "test if an exception is raised when adding data availability XML"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        fake_author_data.return_value = author_data_rows

        fake_add_data_availability.side_effect = Exception("An exception")

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "ModifyMecaXml, exception raised when adding data availability data for"
                " article_id 95901, version 1: An exception"
            ),
        )

    @patch.object(bigquery, "get_author_data")
    @patch.object(activity_module, "get_funding_data")
    @patch.object(bigquery, "get_client")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_no_big_query_funding_data(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_bigquery_get_client,
        fake_get_funding_data,
        fake_author_data,
    ):
        "test if BigQuery returns no funding data"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        fake_get_funding_data.return_value = []

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        fake_author_data.return_value = author_data_rows

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertTrue(
            (
                "ModifyMecaXml, no funding data from BigQuery"
                " for article_id 95901, version 1"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(bigquery, "get_author_data")
    @patch.object(activity_module, "add_funding")
    @patch.object(bigquery, "get_client")
    @patch("docmaptools.parse.get_web_content")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_funding_exception(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_get_web_content,
        fake_bigquery_get_client,
        fake_add_funding,
        fake_author_data,
    ):
        "test if an exception is raised when adding funding XML"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        fake_author_data.return_value = author_data_rows

        fake_add_funding.side_effect = Exception("An exception")

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertEqual(
            self.activity.logger.logexception,
            (
                "ModifyMecaXml, exception raised when adding funding data for"
                " article_id 95901, version 1: An exception"
            ),
        )

    @patch.object(bigquery, "get_author_data")
    @patch.object(bigquery, "get_funding_data")
    @patch.object(bigquery, "get_client")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_author_data_empty(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_bigquery_get_client,
        fake_funding_data,
        fake_author_data,
    ):
        "test if no author data is found"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        funding_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        fake_funding_data.return_value = funding_data_rows

        fake_author_data.return_value = []

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertTrue(
            (
                "ModifyMecaXml, no author data from BigQuery"
                " for article_id 95901, version 1"
            )
            in self.activity.logger.loginfo
        )

    @patch.object(activity_module, "add_author_orcid")
    @patch.object(bigquery, "get_funding_data")
    @patch.object(bigquery, "get_client")
    @patch.object(utils, "get_current_datetime")
    @patch.object(activity_module, "storage_context")
    @patch.object(activity_module, "get_session")
    def test_author_data_exception(
        self,
        fake_session,
        fake_storage_context,
        fake_datetime,
        fake_bigquery_get_client,
        fake_funding_data,
        fake_add_author_orcid,
    ):
        "test if and excepiton is raised adding author data"
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

        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        funding_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        fake_funding_data.return_value = funding_data_rows

        author_data_rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        exception_message = "An exception"
        fake_add_author_orcid.side_effect = Exception(exception_message)

        # do the activity
        result = self.activity.do_activity(test_activity_data.ingest_meca_data)
        # assertions
        self.assertEqual(result, True)
        self.assertEqual(
            (
                "ModifyMecaXml, exception raised when adding author ORCID data"
                " for article_id 95901, version 1: %s" % exception_message
            ),
            self.activity.logger.logexception,
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
        expected = "<article><front><article-meta /></front></article>"
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


class TestGetDataAvailabilityData(unittest.TestCase):
    "test for get_data_availability_data()"

    def setUp(self):
        self.article_id = 95901
        self.version = 1
        self.caller_name = "ModifyMecaXml"
        self.logger = FakeLogger()

    @patch.object(bigquery, "get_client")
    def test_get_data_availability_data(self, fake_bigquery_get_client):
        "test getting data availability data using BigQuery"
        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            [bigquery_test_data.PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT]
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client

        # invoke
        result = activity_module.get_data_availability_data(
            self.article_id, self.version, settings_mock, self.caller_name, self.logger
        )
        # assert
        self.assertIsNotNone(result)

    @patch.object(bigquery, "get_data_availability_data")
    @patch.object(bigquery, "get_client")
    def test_exception(self, fake_bigquery_get_client, fake_get_data):
        "test an exception is raised getting data from BigQuery"
        client = FakeBigQueryClient([])
        fake_bigquery_get_client.return_value = client
        exception_message = "An exception"
        fake_get_data.side_effect = Exception(exception_message)
        # invoke
        activity_module.get_data_availability_data(
            self.article_id,
            self.version,
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertEqual(
            (
                "%s, exception getting data availability data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (self.caller_name, self.article_id, self.version, exception_message),
            self.logger.logexception,
        )


class TestGetFundingData(unittest.TestCase):
    "tests for get_funding_data()"

    def setUp(self):
        self.article_id = 95901
        self.version = 1
        self.caller_name = "ModifyMecaXml"
        self.logger = FakeLogger()

    @patch.object(bigquery, "get_client")
    def test_get_funding_data(self, fake_bigquery_get_client):
        "test getting funding data from BigQuery"
        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_FUNDING_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client
        # invoke
        result = activity_module.get_funding_data(
            self.article_id,
            self.version,
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertIsNotNone(result)

    @patch.object(bigquery, "get_funding_data")
    @patch.object(bigquery, "get_client")
    def test_exception(self, fake_bigquery_get_client, fake_get_data):
        "test exception raised when getting funding data from BigQuery"
        client = FakeBigQueryClient([])
        fake_bigquery_get_client.return_value = client
        exception_message = "An exception"
        fake_get_data.side_effect = Exception(exception_message)
        # invoke
        activity_module.get_funding_data(
            self.article_id,
            self.version,
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertEqual(
            (
                "%s, exception getting funding data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (self.caller_name, self.article_id, self.version, exception_message),
            self.logger.logexception,
        )


class TestGetAuthorData(unittest.TestCase):
    "tests for get_author_data()"

    def setUp(self):
        self.article_id = 95901
        self.version = 1
        self.caller_name = "ModifyMecaXml"
        self.logger = FakeLogger()

    @patch.object(bigquery, "get_client")
    def test_get_author_data(self, fake_bigquery_get_client):
        "test getting author data from BigQuery"
        # mock BigQuery
        rows = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        client = FakeBigQueryClient(rows)
        fake_bigquery_get_client.return_value = client
        # invoke
        result = activity_module.get_author_data(
            self.article_id,
            self.version,
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertIsNotNone(result)

    @patch.object(bigquery, "get_author_data")
    @patch.object(bigquery, "get_client")
    def test_exception(self, fake_bigquery_get_client, fake_get_data):
        "test exception raised when getting author data from BigQuery"
        client = FakeBigQueryClient([])
        fake_bigquery_get_client.return_value = client
        exception_message = "An exception"
        fake_get_data.side_effect = Exception(exception_message)
        # invoke
        activity_module.get_author_data(
            self.article_id,
            self.version,
            settings_mock,
            self.caller_name,
            self.logger,
        )
        # assert
        self.assertEqual(
            (
                "%s, exception getting author data from"
                " BigQuery for article_id %s, version %s: %s"
            )
            % (self.caller_name, self.article_id, self.version, exception_message),
            self.logger.logexception,
        )


class TestAuthorDetailListFromXml(unittest.TestCase):
    "tests for author_detail_list_from_xml()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_author_detail_list_from_xml(self):
        "test collecting author data from XML used for ORCID matching and comparison"
        directory = TempDirectory()
        # use XML from MECA file test fixture
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        xml_file_name = "content/24301711.xml"
        xml_path = os.path.join(directory.path, xml_file_name)
        with zipfile.ZipFile(meca_file_path) as open_zip:
            open_zip.extract(xml_file_name, directory.path)
        with open(xml_path, "rb") as open_file:
            xml_root = ElementTree.fromstring(open_file.read())

        expected = [
            {
                "last_name": "Liang",
                "first_name": "Jie",
                "ORCID": "http://orcid.org/0000-0002-3613-8488",
            },
            {"last_name": "Pan", "first_name": "Yang", "ORCID": None},
            {"last_name": "Zhang", "first_name": "Wenya", "ORCID": None},
            {"last_name": "Gao", "first_name": "Darui", "ORCID": None},
            {"last_name": "Wang", "first_name": "Yongqian", "ORCID": None},
            {
                "last_name": "Xie",
                "first_name": "Wuxiang",
                "ORCID": "http://orcid.org/0000-0001-7527-1022",
            },
            {
                "last_name": "Zheng",
                "first_name": "Fanfan",
                "ORCID": "http://orcid.org/0000-0003-2767-2600",
            },
        ]
        # invoke
        result = activity_module.author_detail_list_from_xml(xml_root)
        # assert
        self.assertEqual(result, expected)


class TestAuthorTokenValue(unittest.TestCase):
    "tests for author_token_value()"

    def test_author_token_value(self):
        "test generating author_token values"
        passes = [
            {"last_name": None, "first_name": None, "expected": "None"},
            {"last_name": "Liang", "first_name": None, "expected": "Liang"},
            {"last_name": "Liang", "first_name": "Jie", "expected": "Liang, J"},
        ]

        for test_data in passes:
            # invoke
            author_token = activity_module.author_token_value(
                test_data.get("last_name"), test_data.get("first_name")
            )
            # assert
            self.assertEqual(
                author_token,
                test_data.get("expected"),
                'last_name %s and first_name %s did not generate "%s"'
                % (
                    test_data.get("last_name"),
                    test_data.get("first_name"),
                    test_data.get("expected"),
                ),
            )


class TestGetXmlAuthorTransformations(unittest.TestCase):
    "tests for get_xml_author_transformations()"

    def test_get_xml_author_transformations(self):
        "test matching various author XML data with ORCID data to be modified"
        xml_author_list = [
            {
                "last_name": "Liang",
                "first_name": "Jie",
                "ORCID": "http://orcid.org/0000-0002-3613-8488",
            },
            {"last_name": "Pan", "first_name": "Yang", "ORCID": None},
            {
                "last_name": "Zhang",
                "first_name": "Wenya",
                "ORCID": "http://orcid.org/0000-0000-0000-0001",
            },
            {
                "last_name": "Xie",
                "first_name": "Wuxiang",
                "ORCID": "http://orcid.org/0000-0001-7527-1022",
            },
        ]

        # abbreviated and modified author_details for test coverage
        author_details = [
            {
                "person_id": "351476",
                "name": "Wuxiang Xie",
                "title": None,
                "first_name": "Wuxiang",
                "middle_name": None,
                "last_name": "Xie",
                "position": 6,
                "is_corresponding_author": False,
                "ORCID": None,
            },
            {
                "person_id": "351473",
                "name": "Wenya Zhang",
                "title": None,
                "first_name": "Wenya",
                "middle_name": None,
                "last_name": "Zhang",
                "position": 3,
                "is_corresponding_author": False,
                "ORCID": "0000-0000-0000-0002",
            },
            {
                "person_id": "351477",
                "name": "Fanfan Zheng",
                "title": None,
                "first_name": "Fanfan",
                "middle_name": None,
                "last_name": "Zheng",
                "position": 7,
                "is_corresponding_author": True,
                "ORCID": "0000-0003-2767-2600",
            },
            {
                "person_id": "351472",
                "name": "Yang Pan",
                "title": None,
                "first_name": "Yang",
                "middle_name": None,
                "last_name": "Pan",
                "position": 2,
                "is_corresponding_author": False,
                "ORCID": "0000-0000-0000-0000",
            },
            {
                "person_id": "351447",
                "name": "Jie Liang",
                "title": "Ms.",
                "first_name": "Jie",
                "middle_name": None,
                "last_name": "Liang",
                "position": 1,
                "is_corresponding_author": False,
                "ORCID": "0000-0002-3613-8488",
            },
        ]

        expected = [
            {
                "action": "modify",
                "author_token": "Liang, J",
                "ORCID": "0000-0002-3613-8488",
            },
            {"action": "add", "author_token": "Pan, Y", "ORCID": "0000-0000-0000-0000"},
            {
                "action": "add",
                "author_token": "Zhang, W",
                "ORCID": "0000-0000-0000-0002",
            },
        ]
        # invoke
        result = activity_module.get_xml_author_transformations(
            xml_author_list, author_details
        )
        # assert
        self.assertEqual(result, expected)

    def test_empty_arguments(self):
        "test if arguments are empty of data"
        xml_author_list = []
        author_details_map = {}
        expected = []
        # invoke
        result = activity_module.get_xml_author_transformations(
            xml_author_list, author_details_map
        )
        # assert
        self.assertEqual(result, expected)


class TestModifyAuthorXml(unittest.TestCase):
    "tests for modify_author_xml()"

    def test_modify_author_xml(self):
        "test modifying XML with author transformation data"
        xml_string = (
            b"<contrib-group>"
            b'<contrib contrib-type="author">'
            b'<contrib-id contrib-id-type="orcid">'
            b"http://orcid.org/0000-0002-3613-8488"
            b"</contrib-id>"
            b"<name><surname>Liang</surname><given-names>Jie</given-names></name>"
            b"</contrib>"
            b'<contrib contrib-type="author">'
            b"<name><surname>Zhang</surname><given-names>Wenya</given-names></name>"
            b"</contrib>"
            b'<contrib contrib-type="author">'
            b'<contrib-id contrib-id-type="orcid">'
            b"https://orcid.org/0000-0000-0000-0000"
            b"</contrib-id>"
            b"<name><surname>Pan</surname><given-names>Yang</given-names></name>"
            b"</contrib>"
            b"</contrib-group>"
        )
        xml_root = ElementTree.fromstring(xml_string)
        author_transformations = [
            {
                "action": "add",
                "author_token": "Zhang, W",
                "ORCID": "0000-0000-0000-0002",
            },
            {"action": "add", "author_token": "Pan, Y", "ORCID": "0000-0000-0000-0001"},
            {
                "action": "modify",
                "author_token": "Liang, J",
                "ORCID": "0000-0002-3613-8488",
            },
        ]
        expected = (
            "<contrib-group>"
            '<contrib contrib-type="author">'
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "http://orcid.org/0000-0002-3613-8488"
            "</contrib-id>"
            "<name><surname>Liang</surname><given-names>Jie</given-names></name>"
            "</contrib>"
            '<contrib contrib-type="author">'
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "https://orcid.org/0000-0000-0000-0002"
            "</contrib-id>\n"
            "<name><surname>Zhang</surname><given-names>Wenya</given-names></name>"
            "</contrib>"
            '<contrib contrib-type="author">'
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "https://orcid.org/0000-0000-0000-0001"
            "</contrib-id>\n"
            '<contrib-id contrib-id-type="orcid">'
            "https://orcid.org/0000-0000-0000-0000"
            "</contrib-id>"
            "<name><surname>Pan</surname><given-names>Yang</given-names></name>"
            "</contrib>"
            "</contrib-group>"
        )
        # invoke
        activity_module.modify_author_xml(xml_root, author_transformations)
        # assert
        result = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertEqual(result, expected)


class TestAddAuthorOrcid(unittest.TestCase):
    "tests for add_author_orcid()"

    def tearDown(self):
        TempDirectory.cleanup_all()

    def test_add_author_orcid(self):
        "test the main function to alter author XML using externally gathered ORCID data"
        directory = TempDirectory()
        # use XML from MECA file test fixture
        meca_file_path = "tests/files_source/95901-v1-meca.zip"
        xml_file_name = "content/24301711.xml"
        xml_path = os.path.join(directory.path, xml_file_name)
        with zipfile.ZipFile(meca_file_path) as open_zip:
            open_zip.extract(xml_file_name, directory.path)
        with open(xml_path, "rb") as open_file:
            xml_root = ElementTree.fromstring(open_file.read())

        author_data = FakeBigQueryRowIterator(
            bigquery_test_data.PREPRINT_95901_V1_AUTHOR_DETAILS_RESULT
        )
        caller_name = "test"
        logger = FakeLogger()

        # invoke
        activity_module.add_author_orcid(xml_root, author_data, caller_name, logger)
        # assert
        xml_string = ElementTree.tostring(xml_root).decode("utf-8")
        self.assertTrue(
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "http://orcid.org/0000-0002-3613-8488"
            "</contrib-id>\n"
            "<name><surname>Liang</surname><given-names>Jie</given-names></name>"
            in xml_string
        )

        self.assertTrue(
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "https://orcid.org/0000-0000-0000-0000"
            "</contrib-id>\n"
            "<name><surname>Pan</surname><given-names>Yang</given-names></name>"
            in xml_string
        )
        self.assertTrue(
            '<contrib-id contrib-id-type="orcid">'
            "http://orcid.org/0000-0001-7527-1022"
            "</contrib-id>\n"
            "<name><surname>Xie</surname><given-names>Wuxiang</given-names></name>"
            in xml_string
        )

        self.assertTrue(
            '<contrib-id contrib-id-type="orcid" authenticated="true">'
            "http://orcid.org/0000-0003-2767-2600"
            "</contrib-id>\n"
            "<name><surname>Zheng</surname><given-names>Fanfan</given-names></name>"
            in xml_string
        )

    def test_empty_author_data(self):
        "test if author_data argument is empty"
        xml_root = None
        author_data = []
        caller_name = "test"
        logger = FakeLogger()
        # invoke
        activity_module.add_author_orcid(xml_root, author_data, caller_name, logger)
        # assert
        self.assertTrue(
            "test, parsed no author_details from author_data" in logger.loginfo
        )
