import base64
import re
from github import Github
from github import GithubException
from provider import utils


class RetryException(RuntimeError):
    pass


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


def detail_from_issue_title(title):
    "extract the article ID and verison from the issue title"
    match = re.match(ISSUE_TITLE_MATCH_PATTERN, title)
    if match:
        return int(match.group("msid")), int(match.group("version"))
    return None, None


def find_github_issues(token, repo_name, version_doi):
    "find the github issues for the article version"
    github_object = Github(token)
    user = github_object.get_user(GITHUB_USER)
    repo = user.get_repo(repo_name)
    doi, version = utils.version_doi_parts(version_doi)
    article_id = utils.msid_from_doi(doi)
    # find the matching issue and return it
    open_issues = repo.get_issues(state="open")
    issues = []
    for issue in open_issues:
        if match_issue_title(issue.title, article_id, version):
            issues.append(issue)
    return issues


def find_github_issue(token, repo_name, version_doi):
    "find the first github issue for the article version"
    for issue in find_github_issues(token, repo_name, version_doi):
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
            issues = find_github_issues(
                settings.github_token,
                settings.preprint_issues_repo_name,
                version_doi,
            )
            for issue in issues:
                add_github_comment(issue, issue_comment)
        except Exception as exception:
            logger.exception(
                (
                    "%s, exception when adding a comment to Github "
                    "for version DOI %s - Details: %s"
                )
                % (caller_name, version_doi, str(exception))
            )


def find_github_issues_by_assignee(token, repo_name, assignee, state="open"):
    "find github issues assigned to assignee of state specified"
    github_object = Github(token)
    user = github_object.get_user(GITHUB_USER)
    repo = user.get_repo(repo_name)
    # find the matching issues and return a list
    return repo.get_issues(state=state, assignee=assignee)


def remove_github_issue_assignee(issue, named_user):
    "remove assignee from the github issue"
    issue.remove_from_assignees(named_user)


def add_label_to_github_issue(issue, label):
    "add a label to the github issue"
    issue.add_to_labels(label)


def update_github(settings, logger, repo_file, content):
    "add or update XML file in github repository"
    github_object = Github(settings.github_token)
    user = github_object.get_user(GITHUB_USER)
    article_xml_repo = user.get_repo(settings.git_repo_name)
    try:
        xml_file = article_xml_repo.get_contents(repo_file)
    except GithubException as exception:
        logger.info("GithubException - description: " + str(exception))
        logger.info(
            "GithubException: file "
            + repo_file
            + " may not exist in github yet. We will try to add it in the repo."
        )
        try:
            response = article_xml_repo.create_file(repo_file, "Creates XML", content)
        except GithubException as inner_exception:
            _retry_or_cancel(inner_exception, logger)
        return "File " + repo_file + " successfully added. Commit: " + str(response)

    except Exception as exception:
        logger.info("Exception: file " + repo_file + ". Error: " + str(exception))
        raise

    # check for file size over limit will have encoding of none
    if xml_file.encoding == "base64":
        repo_file_content = xml_file.decoded_content
    else:
        # use alternate method for large files
        try:
            repo_file_content = base64.b64decode(
                article_xml_repo.get_git_blob(xml_file.sha).content
            )
        except Exception as exception:
            logger.info(
                "Exception: using get_git_blob for file "
                + repo_file
                + ". Error: "
                + str(exception)
            )
            raise

    try:
        # check for changes first
        if isinstance(content, str):
            # encode content to compare bytestring to bytestring
            if content == utils.unicode_encode(repo_file_content):
                return "No changes in file " + repo_file
        elif content == repo_file_content:
            return "No changes in file " + repo_file

        # there are changes
        try:
            response = article_xml_repo.update_file(
                repo_file, "Updates xml", content, xml_file.sha
            )
        except GithubException as exception:
            _retry_or_cancel(exception, logger)
        return "File " + repo_file + " successfully updated. Commit: " + str(response)

    except Exception as exception:
        logger.info("Exception: file " + repo_file + ". Error: " + str(exception))
        raise


def _retry_or_cancel(exception, logger):
    if exception.status == 409:
        logger.warning("Retrying because of exception: %s" % exception)
        raise RetryException(str(exception))

    raise exception
