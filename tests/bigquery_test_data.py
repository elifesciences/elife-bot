import datetime
from google.cloud.bigquery.table import Row
from google.cloud._helpers import UTC


ARTICLE_RESULT_15747 = Row(
    (
        (
            "legacy_site",
            "15747",
            "10.7554/eLife.15747",
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=UTC),
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=UTC),
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=UTC),
            False,
            [
                {
                    "Title": "Dr.",
                    "Last_Name": "Baldwin",
                    "Middle_Name": None,
                    "Role": "Senior Editor",
                    "ORCID": None,
                    "First_Name": "Ian",
                    "Person_ID": "1013",
                },
                {
                    "Title": "",
                    "Last_Name": "Bergstrom",
                    "Middle_Name": None,
                    "Role": "Reviewing Editor",
                    "ORCID": None,
                    "First_Name": "Carl",
                    "Person_ID": "1046",
                },
            ],
        )
    ),
    {
        "Source_Site_ID": 0,
        "Manuscript_ID": 1,
        "DOI": 2,
        "Review_Comment_UTC_Timestamp": 3,
        "Editor_Evaluation_UTC_Timestamp": 4,
        "Author_Response_UTC_Timestamp": 5,
        "Is_Accepted": 6,
        "Reviewers_And_Editors": 7,
    },
)

ARTICLE_RESULT_84364 = Row(
    (
        (
            "legacy_site",
            "84364",
            "10.7554/eLife.84364",
            datetime.datetime(2023, 2, 13, 11, 31, 1, tzinfo=UTC),
            datetime.datetime(2023, 2, 13, 11, 31, 1, tzinfo=UTC),
            datetime.datetime(2023, 2, 10, 6, 28, 43, tzinfo=UTC),
            False,
            [
                {
                    "Title": "Dr.",
                    "Last_Name": "Eisen",
                    "Middle_Name": "B",
                    "Role": "Reviewing Editor",
                    "ORCID": "test-orcid",
                    "First_Name": "Michael",
                    "Person_ID": "1013",
                },
            ],
        )
    ),
    {
        "Source_Site_ID": 0,
        "Manuscript_ID": 1,
        "DOI": 2,
        "Review_Comment_UTC_Timestamp": 3,
        "Editor_Evaluation_UTC_Timestamp": 4,
        "Author_Response_UTC_Timestamp": 5,
        "Is_Accepted": 6,
        "Reviewers_And_Editors": 7,
    },
)

PREPRINT_95901_V1_DATA_AVAILABILITY_RESULT = Row(
    (
        "95901",
        "1",
        "eLife-RP-RA-2023-89331R2",
        "<xml>\n  <data_availability_textbox>Sequencing data (fastq) is available in the Sequence Read Archive (SRA) with the BioProject identification PRJNA934938.  \n\nScripts used for ChIP-seq, RNA-seq, and VSG-seq analysis are available at https://github.com/cestari-lab/lab_scripts. \n\nA specific pipeline was developed for clonal VSG-seq analysis, available at https://github.com/cestari-lab/VSG-Bar-seq.</data_availability_textbox>\n  <datasets>\n    <dataset>\n      <seq_no>1</seq_no>\n      <authors_text_list>Touray AO, Rajesh R, Isebe I, Sternlieb T, Loock M, Kutova O, Cestari I</authors_text_list>\n      <id>https://dataview.ncbi.nlm.nih.gov/object/PRJNA934938</id>\n      <license_info>SRA Bioproject PRJNA934938</license_info>\n      <title>Trypanosoma brucei brucei strain:Lister 427 DNA or RNA sequencing</title>\n      <year>2023</year>\n    </dataset>\n    <datasets_ind>1</datasets_ind>\n    <dryad_ind>0</dryad_ind>\n    <reporting_standards_ind>0</reporting_standards_ind>\n  </datasets>\n  <prev_published_datasets>\n    <dataset>\n      <seq_no>1</seq_no>\n      <authors_text_list>B. Akiyoshi, K. Gull</authors_text_list>\n      <id>https://www.ncbi.nlm.nih.gov/sra/?term=SRP031518</id>\n      <license_info>SRA, accession numbers SRR1023669\tand SRX372731</license_info>\n      <title>Trypanosoma brucei KKT2 ChIP</title>\n      <year>2014</year>\n    </dataset>\n    <datasets_ind>1</datasets_ind>\n    <dryad_ind>0</dryad_ind>\n  </prev_published_datasets>\n</xml>",
    ),
    {
        "manuscript_id": 0,
        "manuscript_version_str": 1,
        "long_manuscript_identifier": 2,
        "data_availability_xml": 3,
    },
)
