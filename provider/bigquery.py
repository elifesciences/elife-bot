from google.cloud.bigquery import Client, QueryJobConfig, ScalarQueryParameter
from google.auth.exceptions import DefaultCredentialsError


BIG_QUERY_VIEW_NAME = (
    "elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit"
)

BIG_QUERY_PREPRINT_VIEW_NAME = (
    "elife-data-pipeline.prod.v_latest_reviewed_preprint_publication_date"
)


class Manuscript:
    """manuscript data populated from BigQuery row"""

    def __init__(self, row=None):
        self.attr_name_map = {
            "Manuscript_ID": "manuscript_id",
            "DOI": "doi",
            "Review_Comment_UTC_Timestamp": "decision_letter_datetime",
            "Author_Response_UTC_Timestamp": "author_response_datetime",
        }
        self.manuscript_id = None
        self.doi = None
        self.decision_letter_datetime = None
        self.author_response_datetime = None
        # todo!! get the referee report date from BigQuery once the view includes a field for it
        self.referee_report_datetime = None
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
        if hasattr(row, "Reviewers_And_Editors"):
            for row_dict in row.Reviewers_And_Editors:
                reviewer = Reviewer(row_dict)
                self.reviewers.append(reviewer)


class Reviewer:
    def __init__(self, row_dict=None):
        self.attr_name_map = {
            "Title": "title",
            "Last_Name": "last_name",
            "Middle_Name": "middle_name",
            "Role": "role",
            "ORCID": "orcid",
            "First_Name": "first_name",
            "Person_ID": "person_id",
        }
        self.title = None
        self.last_name = None
        self.middle_name = None
        self.role = None
        self.orcid = None
        self.first_name = None
        self.person_id = None

        # populate from the row dict
        self.populate_from_dict(row_dict)

    def populate_from_dict(self, row_dict):
        if not row_dict:
            return
        # populate the primary values
        for row_key, attr_name in list(self.attr_name_map.items()):
            setattr(self, attr_name, row_dict.get(row_key, None))


class Preprint:
    "data struct for preprint dates and other data"

    def __init__(self, row_dict=None):
        self.attr_name_map = {
            "elife_doi": "doi",
            "elife_doi_version": "version",
            "publication_date": "publication_date",
            "utc_publication_time": "utc_publication_time",
        }
        self.doi = None
        self.version = None
        self.publication_date = None
        self.utc_publication_time = None

        # populate from the row dict
        self.populate_from_dict(row_dict)

    def populate_from_dict(self, row):
        if not row:
            return
        # populate the object values
        for row_key, attr_name in list(self.attr_name_map.items()):
            setattr(self, attr_name, getattr(row, row_key, None))


def get_client(settings, logger):
    """path to credentials file in env var GOOGLE_APPLICATION_CREDENTIALS"""
    try:
        return Client(project=settings.big_query_project_id)
    except DefaultCredentialsError:
        logger.info("Failed to instantiate a bigquery Client")
        raise


def article_query():
    return ("SELECT * " "FROM `{view_name}` WHERE DOI = @doi").format(
        view_name=BIG_QUERY_VIEW_NAME
    )


def article_data(client, doi):
    query = article_query()
    job_config = QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter("doi", "STRING", doi),
        ]
    )
    query_job = client.query(query, job_config=job_config)  # API request
    return query_job.result()  # Waits for query to finish


def date_to_string(datetime_date):
    return datetime_date.strftime("%Y-%m-%d")


def get_review_date(manuscript_object, article_type):
    """get date for a peer review sub article"""
    if article_type in ["article-commentary", "decision-letter", "editor-report"]:
        if manuscript_object.decision_letter_datetime:
            return date_to_string(manuscript_object.decision_letter_datetime)
    elif article_type in ["author-comment", "reply"]:
        if manuscript_object.author_response_datetime:
            return date_to_string(manuscript_object.author_response_datetime)
        if manuscript_object.decision_letter_datetime:
            return date_to_string(manuscript_object.decision_letter_datetime)
    elif article_type == "referee-report":
        if manuscript_object.referee_report_datetime:
            return date_to_string(manuscript_object.referee_report_datetime)
        if manuscript_object.decision_letter_datetime:
            return date_to_string(manuscript_object.decision_letter_datetime)
    return None


def preprint_article_query(date_string=None, day_interval=None):
    "query for preprint publication dates, optionally filter by publication_date range"
    where_clause = ""
    if date_string and day_interval:
        where_clause = (
            "WHERE `publication_date` "
            "between DATE_SUB(@date_string, INTERVAL @day_interval DAY) AND @date_string"
        )
    return "SELECT * FROM `{view_name}` {where_clause} ORDER BY publication_date DESC".format(
        view_name=BIG_QUERY_PREPRINT_VIEW_NAME, where_clause=where_clause
    )


def preprint_article_result(client, date_string=None, day_interval=None):
    "run a preprint article query and return the query result"
    query = preprint_article_query(date_string, day_interval)
    job_config = QueryJobConfig(
        query_parameters=[
            ScalarQueryParameter("date_string", "STRING", date_string),
            ScalarQueryParameter("day_interval", "INTEGER", day_interval),
        ]
    )
    query_job = client.query(query, job_config=job_config)  # API request
    return query_job.result()  # Waits for query to finish


def preprint_objects(query_result):
    "from a preprint query result, return a list of populated objects"
    return [Preprint(row_dict=row) for row in query_result]
