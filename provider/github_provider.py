import re
from github import Github
from provider import utils

GITHUB_USER = "elifesciences"

ISSUE_TITLE_MATCH_PATTERN = re.compile(
    r"^MSID: (?P<msid>\d+?) Version: (?P<version>\d+?).*"
)


def match_issue_title(title, article_id, version):
    "check if Github issue title is for the article version"
    match = re.match(ISSUE_TITLE_MATCH_PATTERN, title)
    if match:
        if int(match.group("msid")) == int(article_id) and int(
            match.group("version")
        ) == int(version):
            return True
    return False


def find_github_issue(token, repo_name, version_doi):
    "find the github issue for the article version"
    github_object = Github(token)
    user = github_object.get_user(GITHUB_USER)
    repo = user.get_repo(repo_name)
    doi, version = utils.version_doi_parts(version_doi)
    article_id = utils.msid_from_doi(doi)
    # find the matching issue and return it
    open_issues = repo.get_issues(state="open")
    for issue in open_issues:
        if match_issue_title(issue.title, article_id, version):
            return issue
    return None


def add_github_comment(issue, message):
    "add a github comment to the issue"
    issue.create_comment(message)


def add_github_issue_comment(settings, logger, caller_name, version_doi, issue_comment):
    "add the message as a github preprint issue comment"
    if (
        hasattr(settings, "github_token")
        and hasattr(settings, "preprint_issues_repo_name")
        and settings.github_token
        and settings.preprint_issues_repo_name
    ):
        try:
            issue = find_github_issue(
                settings.github_token,
                settings.preprint_issues_repo_name,
                version_doi,
            )
            if issue:
                add_github_comment(issue, issue_comment)
        except Exception as exception:
            logger.exception(
                (
                    "%s, exception when adding a comment to Github "
                    "for version DOI %s - Details: %s"
                )
                % (caller_name, version_doi, str(exception))
            )
