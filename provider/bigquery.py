from google.oauth2 import service_account
from google.cloud.bigquery import Client


CREDENTIALS_SCOPE = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/bigquery'
]

BIG_QUERY_VIEW_NAME = 'elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit'


class Manuscript():
    """manuscript data populated from BigQuery row"""
    def __init__(self, row=None):
        self.attr_name_map = {
            'Manuscript_ID': 'manuscript_id',
            'DOI': 'doi',
            'QC_Complete_Timestamp': 'qc_complete_datetime',
            'Decision_Sent_Timestamp': 'decision_sent_datetime'
        }
        self.manuscript_id = None
        self.doi = None
        self.qc_complete_datetime = None
        self.decision_sent_datetime = None
        self.reviewers = []
        # populate values from the row data
        self.populate_from_row(row)

    def populate_from_row(self, row):
        if not row:
            return
        # populate the primary values
        for row_key, attr_name in list(self.attr_name_map.items()):
            setattr(self, attr_name, getattr(row, row_key, None))
        # populate the reviewers
        if hasattr(row, 'Reviewers_And_Editors'):
            for row_dict in row.Reviewers_And_Editors:
                reviewer = Reviewer(row_dict)
                self.reviewers.append(reviewer)


class Reviewer():

    def __init__(self, row_dict=None):
        self.attr_name_map = {
            'Name': 'name',
            'ORCID': 'orcid',
            'Title': 'title',
            'Person_ID': 'person_id'
        }
        self.name = None
        self.orcid = None
        self.title = None
        self.person_id = None
        self.roles = []
        # populate from the row dict
        self.populate_from_dict(row_dict)

    def populate_from_dict(self, row_dict):
        if not row_dict:
            return
        # populate the primary values
        for row_key, attr_name in list(self.attr_name_map.items()):
            setattr(self, attr_name, row_dict.get(row_key, None))
        # populate the roles
        self.roles = row_dict.get('Roles', [])


def get_credentials(settings):
    credentials = service_account.Credentials.from_service_account_file(
        settings.big_query_credentials_file)
    return credentials.with_scopes(CREDENTIALS_SCOPE)


def get_client(settings):
    scoped_credentials = get_credentials(settings)
    return Client(
        credentials=scoped_credentials,
        project=settings.big_query_project_id)


def article_query(doi):
    return (
        'SELECT * '
        'FROM `{view_name}` '
        'WHERE DOI = "{doi}" ').format(
            view_name=BIG_QUERY_VIEW_NAME,
            doi=doi
        )


def article_data(client, doi):
    query = article_query(doi)
    query_job = client.query(query)  # API request
    return query_job.result()  # Waits for query to finish


def date_to_string(datetime_date):
    return datetime_date.strftime('%Y-%m-%d')


def get_review_date(doi, article_type):
    """get date for a peer review sub article"""
    # todo!!! actual query logic and real data
    return '1970-01-02'
