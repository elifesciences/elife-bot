from google.cloud.bigquery import Client
from google.auth.exceptions import DefaultCredentialsError


BIG_QUERY_VIEW_NAME = (
    "elife-data-pipeline.prod.mv_Production_Manuscript_Crossref_Deposit"
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


def get_client(settings, logger):
    """path to credentials file in env var GOOGLE_APPLICATION_CREDENTIALS"""
    try:
        return Client(project=settings.big_query_project_id)
    except DefaultCredentialsError:
        logger.info("Failed to instantiate a bigquery Client")
        raise


def article_query(doi):
    return ("SELECT * " "FROM `{view_name}` " 'WHERE DOI = "{doi}" ').format(
        view_name=BIG_QUERY_VIEW_NAME, doi=doi
    )


def article_data(client, doi):
    query = article_query(doi)
    query_job = client.query(query)  # API request
    return query_job.result()  # Waits for query to finish


def date_to_string(datetime_date):
    return datetime_date.strftime("%Y-%m-%d")


def get_review_date(manuscript_object, article_type):
    """get date for a peer review sub article"""
    if article_type in ["article-commentary", "decision-letter", "editor-report"]:
        if manuscript_object.decision_letter_datetime:
            return date_to_string(manuscript_object.decision_letter_datetime)
    elif article_type == "reply":
        if manuscript_object.author_response_datetime:
            return date_to_string(manuscript_object.author_response_datetime)
        elif manuscript_object.decision_letter_datetime:
            return date_to_string(manuscript_object.decision_letter_datetime)
    return None
