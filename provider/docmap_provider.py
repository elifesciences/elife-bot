import datetime
import json
import requests
from docmaptools import parse
from provider import utils


REPAIR_XML = True

LOG_FILENAME = "elifecleaner.log"
LOG_FORMAT_STRING = (
    "%(asctime)s %(levelname)s %(name)s:%(module)s:%(funcName)s: %(message)s"
)

REQUESTS_TIMEOUT = (10, 60)

# number of hours for published date comparisons
PUBLISHED_DATE_HOURS_DELTA = 0


def docmap_index_url(settings):
    "URL of the preprint docmap index endpoint"
    return getattr(settings, "docmap_index_url", None)


def get_docmap_index(url, logger, user_agent=None):
    "GET request for docmap index json"
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    response = requests.get(url, timeout=REQUESTS_TIMEOUT, headers=headers)
    logger.info("Request to docmaps API: GET %s", url)
    logger.info("Response from docmaps API: %s\n", response.status_code)
    status_code = response.status_code
    if status_code not in [200]:
        raise Exception(("Error looking up docmap URL " + url + ": %s\n") % status_code)

    return response.content


def get_docmap_index_by_account_id(url, account_id, logger, user_agent=None):
    "GET request for the docmap json and return the eLife docmap if a list is returned"
    content = get_docmap_index(url, logger, user_agent=user_agent)
    docmaps = None
    if content:
        logger.info("Parsing docmap index content as JSON for URL %s", url)
        content_json = json.loads(content)
        if not content_json.get("docmaps"):
            logger.info("No docmaps found in docmap index for URL %s", url)
            return None
        docmaps = {"docmaps": []}
        if content_json.get("docmaps"):
            logger.info(
                "Multiple docmaps returned for URL %s, filtering by account_id %s",
                url,
                account_id,
            )
            for list_item in content_json.get("docmaps"):
                sciety_id = list_item.get("publisher", {}).get("account", {}).get("id")
                if sciety_id and sciety_id == account_id:
                    docmaps["docmaps"].append(list_item)
    return docmaps


def get_docmap_index_json(settings, caller_name, logger):
    "get a docmap JSON for the article from endpoint"
    # generate docmap URL
    docmap_endpoint_url = docmap_index_url(settings)
    logger.info("%s, docmap_endpoint_url: %s" % (caller_name, docmap_endpoint_url))
    # get docmap json
    logger.info("%s, getting docmap index string" % caller_name)
    # return docmaps filtered based on account ID
    return get_docmap_index_by_account_id(
        docmap_endpoint_url,
        settings.docmap_account_id,
        logger,
        user_agent=getattr(settings, "user_agent", None),
    )


def content_computer_files(step_dict):
    "find computer-file data in docmap content steps"
    computer_file_list = []
    for content in step_dict.get("content", []):
        if content.get("type") == "computer-file":
            computer_file_list.append(content)
    return computer_file_list


def computer_files(step):
    "return preprint computer-file from step input"
    computer_file_list = []
    for input_dict in parse.step_inputs(step):
        if input_dict.get("type") == "preprint":
            computer_file_list = content_computer_files(input_dict)
    return computer_file_list


def output_computer_files(step):
    "return preprint computer-file from step outputs"
    computer_file_list = []
    actions = parse.step_actions(step)
    if actions:
        for action in actions:
            outputs = parse.action_outputs(action)
            for output_dict in outputs:
                if output_dict.get("type") == "preprint":
                    computer_file_list = content_computer_files(output_dict)
    return computer_file_list


def profile_docmap_steps(docmap_steps_list):
    "collect data about a docmap for the purpose of comparisons"
    # count peer reviews and computer-file inputs
    details = {
        "computer-file-count": 0,
        "peer-review-count": 0,
        "published": None,
    }
    if not docmap_steps_list:
        return details
    for step in docmap_steps_list:
        for action in parse.step_actions(step):
            for output in parse.action_outputs(action):
                if output.get("type") in [
                    "evaluation-summary",
                    "reply",
                    "review-article",
                ]:
                    details["peer-review-count"] += 1
                elif output.get("type") == "preprint" and output.get("published"):
                    details["published"] = output.get("published")
        details["computer-file-count"] += len(computer_files(step))
    return details


def version_doi_step_map(docmap_json):
    "get a version DOI step map from the docmap"
    return parse.preprint_version_doi_step_map(docmap_json)


def docmap_profile_step_map(docmap_index_json):
    "from docmap index create a map of version DOI to docmap profile data"
    full_step_map = {}
    if docmap_index_json:
        for docmap in docmap_index_json.get("docmaps"):
            try:
                step_map = version_doi_step_map(docmap)
            except TypeError:
                continue
            for key, value in step_map.items():
                full_step_map[key] = profile_docmap_steps(value)
    return full_step_map


def check_published_date(datetime_string):
    "check for a published date and how long ago it was"
    if not datetime_string:
        return True
    # compare date
    published_datetime = datetime.datetime.strptime(
        datetime_string, "%Y-%m-%dT%H:%M:%S%z"
    )
    current_datetime = utils.get_current_datetime()
    if current_datetime - published_datetime > datetime.timedelta(
        hours=PUBLISHED_DATE_HOURS_DELTA
    ):
        return False
    return True


def changed_version_doi_data(docmap_index_json, prev_docmap_index_json, logger):
    "compare current and previous docmap lists, return version DOI that have changed"
    ingest_version_doi_list = []
    new_version_doi_list = []
    no_computer_file_version_doi_list = []
    # filter docmaps by attributes compared to previous docmap
    current_step_map = docmap_profile_step_map(docmap_index_json)
    prev_step_map = docmap_profile_step_map(prev_docmap_index_json)
    # compare
    for key, value in current_step_map.items():
        prev_value = prev_step_map.get(key)
        # new DOIs
        if not prev_value:
            new_version_doi_list.append(key)
        # peer reviews and no computer-file
        if value.get("computer-file-count") <= 0 and (
            (not prev_value and value.get("peer-review-count") > 0)
            or (
                prev_value
                and value.get("peer-review-count") > prev_value.get("peer-review-count")
            )
        ):
            no_computer_file_version_doi_list.append(key)
        # DOIs ready to ingest a MECA package
        if (
            not prev_value
            and value.get("computer-file-count") > 0
            and value.get("peer-review-count") > 0
        ):
            if check_published_date(value.get("published")):
                ingest_version_doi_list.append(key)
            else:
                logger.info(
                    "DOI %s omitted, its published date %s is too far in the past"
                    % (key, value.get("published"))
                )
        # if there was a previous docmap, either the computer-file or peer reviews changed
        elif (
            prev_value
            and value.get("computer-file-count") > 0
            and value.get("peer-review-count") > prev_value.get("peer-review-count")
        ) or (
            prev_value
            and value.get("peer-review-count") > 0
            and prev_value.get("computer-file-count") <= 0
            and value.get("computer-file-count") > 0
        ):
            if check_published_date(value.get("published")):
                ingest_version_doi_list.append(key)
            else:
                logger.info(
                    "DOI %s omitted, its published date %s is too far in the past"
                    % (key, value.get("published"))
                )

    return {
        "ingest_version_doi_list": ingest_version_doi_list,
        "new_version_doi_list": new_version_doi_list,
        "no_computer_file_version_doi_list": no_computer_file_version_doi_list,
    }


def computer_file_url_from_steps(method_name, steps, version_doi, caller_name, logger):
    "get computer-file data from docmap steps invoking the method_name"
    computer_file = None
    for step in steps:
        # switch based on the method name
        computer_file_list = []
        if method_name == "computer_files":
            computer_file_list = computer_files(step)
        elif method_name == "output_computer_files":
            computer_file_list = output_computer_files(step)

        if computer_file_list:
            computer_file = computer_file_list[0]
            break

    if not computer_file:
        logger.info(
            "%s, computer_file not found in steps for version DOI %s"
            % (caller_name, version_doi)
        )
        return None
    logger.info(
        "%s, computer_file %s for version_doi %s"
        % (caller_name, computer_file, version_doi)
    )

    return computer_file.get("url")


def input_computer_file_url_from_steps(steps, version_doi, caller_name, logger):
    "get the url of computer-file input from docmap steps"
    return computer_file_url_from_steps(
        "computer_files", steps, version_doi, caller_name, logger
    )


def output_computer_file_url_from_steps(steps, version_doi, caller_name, logger):
    "get the url of computer-file input from docmap steps"
    return computer_file_url_from_steps(
        "output_computer_files", steps, version_doi, caller_name, logger
    )
