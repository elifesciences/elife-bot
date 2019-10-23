from google.oauth2 import service_account
from google.cloud.bigquery import Client


CREDENTIALS_SCOPE = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/bigquery'
]

BIG_QUERY_VIEW_NAME = 'elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit'


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


def get_review_date(doi, article_type):
    """get date for a peer review sub article"""
    # todo!!! actual query logic and real data
    return '1970-01-02'
