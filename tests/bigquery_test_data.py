import datetime
from google.cloud.bigquery.table import Row
from google.cloud._helpers import _UTC


ARTICLE_RESULT_15747 = Row(
    (
        (
            '15747', '10.7554/eLife.15747',
            datetime.datetime(2016, 5, 31, 11, 31, 1, tzinfo=_UTC()),
            datetime.datetime(2016, 6, 10, 6, 28, 43, tzinfo=_UTC()),
            [
                {
                    'Name': 'Ian Baldwin',
                    'ORCID': None,
                    'Title': 'Dr.',
                    'Person_ID': '1013',
                    'Roles': ['Senior Editor']
                },
                {
                    'Name': 'Carl Bergstrom',
                    'ORCID': None,
                    'Title': '',
                    'Person_ID': '1046',
                    'Roles': ['Reviewing Editor']
                }]
            )
        ),
    {
        'Manuscript_ID': 0,
        'DOI': 1,
        'QC_Complete_Timestamp': 2,
        'Decision_Sent_Timestamp': 3,
        'Reviewers_And_Editors': 4
        }
    )
