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
