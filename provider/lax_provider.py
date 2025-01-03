import os
import time
import json
import requests
from dateutil.parser import parse
import log
from provider import utils
from provider.article_structure import ArticleInfo
from provider.storage_provider import storage_context


identity = "process_%s" % os.getpid()
logger = log.logger("lax_provider.log", "INFO", identity, loggerName=__name__)


class ErrorCallingLaxException(Exception):
    pass


def lax_request(
    url, article_id, verify_ssl, request_type="version", auth_key=None, headers=None
):
    "common request logic to Lax"
    request_headers = lax_auth_header(auth_key)
    if headers:
        request_headers.update(headers)
    response = requests.get(url, verify=verify_ssl, headers=request_headers)
    logger.info("Request to lax: GET %s", url)
    logger.info("Response from lax: %s\n%s", response.status_code, response.content)
    status_code = response.status_code
    if status_code not in [200, 404]:
        raise ErrorCallingLaxException(
            "Error looking up article "
            + utils.pad_msid(article_id)
            + " %s in Lax: %s\n%s" % (request_type, status_code, response.content)
        )

    if status_code == 200:
        data = response.json()
        if "versions" in data:
            return status_code, data["versions"]
        else:
            return status_code, data

    return status_code, None


def lax_auth_header(auth_key):
    "headers for requests to lax"
    if auth_key:
        return {"Authorization": auth_key}
    return {}


def lax_auth_key(settings, auth=False):
    "value for the Authorization header in lax for public or auth by key"
    if auth:
        return settings.lax_auth_key
    return "public"


def article_json(article_id, settings, auth=False):
    "get json for the latest article version from lax"
    url = settings.lax_article_endpoint.replace(
        "{article_id}", utils.pad_msid(article_id)
    )
    return lax_request(
        url, article_id, settings.verify_ssl, None, lax_auth_key(settings, auth)
    )


def article_versions(article_id, settings, auth=False):
    "get json for article versions from lax"
    url = settings.lax_article_versions.replace(
        "{article_id}", utils.pad_msid(article_id)
    )
    headers = {}
    if (
        hasattr(settings, "lax_article_versions_accept_header")
        and settings.lax_article_versions_accept_header
    ):
        headers["Accept"] = settings.lax_article_versions_accept_header
    return lax_request(
        url,
        article_id,
        settings.verify_ssl,
        "version",
        lax_auth_key(settings, auth),
        headers=headers,
    )


def article_related(article_id, settings, auth=False):
    "get json for related article data from lax"
    url = settings.lax_article_related.replace(
        "{article_id}", utils.pad_msid(article_id)
    )
    return lax_request(
        url, article_id, settings.verify_ssl, None, lax_auth_key(settings, auth)
    )


def article_snippet(article_id, version, settings, auth=False):
    "snippet from the versions list for this version"
    status_code, data = article_versions(article_id, settings, auth)
    if status_code == 200:
        snippet = next(
            vd for vd in data if vd.get("version") and vd["version"] == int(version)
        )
        return snippet
    raise Exception(
        "Error in article_snippet: Version not found. Status: " + str(status_code)
    )


def article_status_version_map(article_id, settings, auth=False):
    "map article status and a list of versions"
    status_version_map = {}
    status_code, data = article_versions(article_id, settings, auth)
    if status_code == 200:
        for version_data in data:
            if not version_data.get("version"):
                # skip the data if there is no version key, such as for a preprint article
                continue
            if version_data.get("status") not in status_version_map:
                status_version_map[version_data.get("status")] = []
            status_version_map[version_data.get("status")].append(
                version_data.get("version")
            )
    return status_version_map


def article_first_by_status(article_id, version, status, settings, auth=False):
    "for this article version is it the first of its status, e.g. the first vor version"
    status_version_map = article_status_version_map(article_id, settings, auth)
    if not status_version_map or status not in status_version_map:
        return None
    for article_version in status_version_map.get(status):
        if int(article_version) < int(version):
            # we found an article of the status with an earlier version
            return False
    return True


def article_highest_version(article_id, settings, auth=False):
    status_code, data = article_versions(article_id, settings, auth)
    if status_code == 200:
        data_with_a_version = [x for x in data if x.get("version")]
        high_version = (
            0
            if len(data_with_a_version) < 1
            else max([int(x["version"]) for x in data_with_a_version])
        )
        return high_version
    elif status_code == 404:
        return "1"


def article_next_version(article_id, settings):
    version = article_highest_version(article_id, settings)
    if isinstance(version, int) and version >= 0:
        version = str(version + 1)
    if version is None:
        raise RuntimeError(
            "Error looking up article next version. Version is Null. Check call to Lax."
        )
    return version


def article_version_date_by_version(article_id, version, settings):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        version_data = next(
            vd for vd in data if vd.get("version") and vd["version"] == int(version)
        )
        return parse(version_data["versionDate"]).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise Exception(
        "Error in article_publication_date_by_version: Version date not found. Status: "
        + str(status_code)
    )


def article_publication_date(article_id, settings, logger=None):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        first_published_version_list = [
            x for x in data if x.get("version") and int(x["version"]) == 1
        ]
        if len(first_published_version_list) < 1:
            return None
        first_published_version = first_published_version_list[0]
        if "published" not in first_published_version:
            return None
        date_str = None
        try:
            date_struct = time.strptime(
                first_published_version["published"], "%Y-%m-%dT%H:%M:%SZ"
            )
            date_str = time.strftime("%Y%m%d%H%M%S", date_struct)

        except:
            if logger:
                logger.error(
                    "Error parsing the datetime_published from Lax: "
                    + str(first_published_version["published"])
                )

        return date_str
    elif status_code == 404:
        return None
    else:
        if logger:
            logger.error(
                "Error obtaining version information from Lax" + str(status_code)
            )
        return None


def check_status(data, status_type):
    status = None
    for vd in data:
        if vd.get("status") and vd["status"] and vd["status"] == status_type:
            status = True
    return status


def poa_vor_status(data):
    if not data or len(data) < 1:
        return None, None
    poa_status = check_status(data, "poa")
    vor_status = check_status(data, "vor")
    return poa_status, vor_status


def was_ever_poa(article_id, settings):
    "Use Lax data to check if the article was ever a PoA article"
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        poa_status, vor_status = poa_vor_status(data)
        if poa_status is True:
            return True
        else:
            return False
    else:
        return None


def published_considering_poa_status(
    article_id, settings, is_poa, article_was_ever_poa
):
    """
    Check the lax data for whether an article is published
    considering whether it was or is PoA status
    """
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        poa_status, vor_status = poa_vor_status(data)
    else:
        poa_status, vor_status = None, None
    # Now a decision can be made
    if (is_poa is True and article_was_ever_poa is True) or (
        is_poa is False and article_was_ever_poa is False
    ):
        # In this case, any version is sufficient
        if poa_status or vor_status:
            return True
    elif is_poa is False and article_was_ever_poa is True:
        # In the case of was ever PoA but is not PoA
        #  check there is a VoR version
        if vor_status:
            return True
    # Default
    return False


def article_retracted_status(article_id, settings):
    "using related article data is this article retracted"
    retracted_status = None
    status_code, data = article_related(article_id, settings)
    if status_code == 200:
        retracted_status = False
        for related_article in data:
            if related_article.get("type") == "retraction":
                retracted_status = True
    return retracted_status


def prepare_action_message(
    settings,
    article_id,
    run,
    expanded_folder,
    version,
    status,
    action,
    force=False,
    run_type=None,
):
    xml_bucket = settings.publishing_buckets_prefix + settings.expanded_bucket
    xml_file_name = get_xml_file_name(settings, expanded_folder, xml_bucket)
    xml_path = (
        "https://s3-external-1.amazonaws.com/"
        + xml_bucket
        + "/"
        + expanded_folder
        + "/"
        + xml_file_name
    )
    carry_over_data = {
        "action": action,
        "location": xml_path,
        "id": article_id,
        "version": int(version),
        "force": force,
        "token": lax_token(run, version, expanded_folder, status, force, run_type),
    }
    message = carry_over_data
    return message


def get_xml_file_name(settings, expanded_folder, xml_bucket, version=None):
    "s3 path to the article xml file in the expanded folder"
    storage = storage_context(settings)
    resource = settings.storage_provider + "://" + xml_bucket + "/" + expanded_folder
    files_in_bucket = storage.list_resources(resource)
    # remove the subfolder name from file names
    files_in_bucket = [filename.rsplit("/", 1)[-1] for filename in files_in_bucket]
    for filename in files_in_bucket:
        info = ArticleInfo(filename)
        if info.file_type == "ArticleXML":
            if version is None:
                return filename
            v_number = "-v" + version + "."
            if v_number in filename:
                return filename
    return None


def lax_token(run, version, expanded_folder, status, force=False, run_type=None):
    token = {
        "run": run,
        "version": version,
        "expanded_folder": expanded_folder,
        "status": status,
        "force": force,
        "run_type": run_type,
    }
    return utils.base64_encode_string(json.dumps(token))


def message_from_lax(data):
    """
    format a message from a Lax response data
    """
    return data.get("message") if data.get("message") else "(empty message)"
