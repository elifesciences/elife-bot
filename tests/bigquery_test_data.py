import datetime
from google.cloud.bigquery.table import Row
from google.cloud._helpers import UTC


ARTICLE_RESULT_15747 = Row(
    (
        (
            "15747",
            "10.7554/eLife.15747",
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=UTC),
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=UTC),
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
        "Manuscript_ID": 0,
        "DOI": 1,
        "Review_Comment_UTC_Timestamp": 2,
        "Author_Response_UTC_Timestamp": 3,
        "Reviewers_And_Editors": 4,
    },
)
