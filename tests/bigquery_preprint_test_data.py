import datetime
from google.cloud.bigquery.table import Row
from google.cloud._helpers import UTC


PREPRINT_QUERY_RESULT = [
    Row(
        (
            datetime.time(14, 0),
            1,
            {
                "sheet_name": "publication_date",
                "spreadsheet_id": "spreadsheet_id_value",
            },
            datetime.date(2023, 11, 22),
            "10.7554/eLife.92362",
            datetime.datetime(2023, 11, 27, 22, 1, 40, tzinfo=datetime.timezone.utc),
            datetime.datetime(2023, 11, 22, 12, 45, 17, tzinfo=datetime.timezone.utc),
        ),
        {
            "utc_publication_time": 0,
            "elife_doi_version": 1,
            "provenance": 2,
            "publication_date": 3,
            "elife_doi": 4,
            "imported_timestamp": 5,
            "first_imported_timestamp": 6,
        },
    ),
    Row(
        (
            datetime.time(14, 0),
            2,
            {
                "sheet_name": "publication_date",
                "spreadsheet_id": "spreadsheet_id_value",
            },
            datetime.date(2023, 11, 22),
            "10.7554/eLife.87445",
            datetime.datetime(2023, 11, 27, 22, 1, 40, tzinfo=datetime.timezone.utc),
            datetime.datetime(2023, 11, 22, 16, 1, 12, tzinfo=datetime.timezone.utc),
        ),
        {
            "utc_publication_time": 0,
            "elife_doi_version": 1,
            "provenance": 2,
            "publication_date": 3,
            "elife_doi": 4,
            "imported_timestamp": 5,
            "first_imported_timestamp": 6,
        },
    ),
]
