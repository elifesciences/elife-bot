import requests
import time
from . import article
import json
from dateutil.parser import parse
import log
import os
from provider.utils import base64_encode_string


identity = "process_%s" % os.getpid()
logger = log.logger("lax_provider.log", 'INFO', identity, loggerName=__name__)


class ErrorCallingLaxException(Exception):
    pass


def lax_request(
    url, article_id, verify_ssl, request_type="version", auth_key=None, headers=None
):
    "common request logic to Lax"
    auth_headers = lax_auth_header(auth_key)
    request_headers = auth_headers.update(headers) if headers else auth_headers
    response = requests.get(url, verify=verify_ssl, headers=request_headers)
    logger.info("Request to lax: GET %s", url)
    logger.info("Response from lax: %s\n%s", response.status_code, response.content)
    status_code = response.status_code
    if status_code not in [200, 404]:
        raise ErrorCallingLaxException(
            "Error looking up article " + article_id + " %s in Lax: %s\n%s" %
            (request_type, status_code, response.content))

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
        return {'Authorization': auth_key}
    return {}


def lax_auth_key(settings, auth=False):
    "value for the Authorization header in lax for public or auth by key"
    if auth:
        return settings.lax_auth_key
    return 'public'


def article_json(article_id, settings, auth=False):
    "get json for the latest article version from lax"
    url = settings.lax_article_endpoint.replace('{article_id}', article_id)
    return lax_request(url, article_id, settings.verify_ssl, None,
                       lax_auth_key(settings, auth))


def article_versions(article_id, settings, auth=False):
    "get json for article versions from lax"
    url = settings.lax_article_versions.replace("{article_id}", article_id)
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
    url = settings.lax_article_related.replace("{article_id}", article_id)
    return lax_request(
        url, article_id, settings.verify_ssl, None, lax_auth_key(settings, auth)
    )


def article_snippet(article_id, version, settings, auth=False):
    "snippet from the versions list for this version"
    status_code, data = article_versions(article_id, settings, auth)
    if status_code == 200:
        snippet = next(vd for vd in data if vd["version"] == int(version))
        return snippet
    raise Exception("Error in article_snippet: Version not found. Status: " + str(status_code))


def article_status_version_map(article_id, settings, auth=False):
    "map article status and a list of versions"
    status_version_map = {}
    status_code, data = article_versions(article_id, settings, auth)
    if status_code == 200:
        for version_data in data:
            if version_data.get('status') not in status_version_map:
                status_version_map[version_data.get('status')] = []
            status_version_map[version_data.get('status')].append(version_data.get('version'))
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
        high_version = 0 if len(data) < 1 else max([int(x["version"]) for x in data])
        return high_version
    elif status_code == 404:
        return "1"


def article_next_version(article_id, settings):
    version = article_highest_version(article_id, settings)
    if isinstance(version, int) and version >= 0:
        version = str(version + 1)
    if version is None:
        raise RuntimeError("Error looking up article next version. Version is Null. Check call to Lax.")
    return version


def article_version_date_by_version(article_id, version, settings):
    status_code, data = article_versions(article_id, settings)
    print(data)
    if status_code == 200:
        version_data = next(vd for vd in data if vd["version"] == int(version))
        return parse(version_data["versionDate"]).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise Exception("Error in article_publication_date_by_version: Version date not found. Status: " + str(status_code))


def article_publication_date(article_id, settings, logger=None):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        first_published_version_list = [x for x in data if int(x['version']) == 1]
        if len(first_published_version_list) < 1:
            return None
        first_published_version = first_published_version_list[0]
        if "published" not in first_published_version:
            return None
        date_str = None
        try:
            date_struct = time.strptime(first_published_version['published'], "%Y-%m-%dT%H:%M:%SZ")
            date_str = time.strftime('%Y%m%d%H%M%S', date_struct)

        except:
            if logger:
                logger.error("Error parsing the datetime_published from Lax: "
                             + str(first_published_version['published']))

        return date_str
    elif status_code == 404:
        return None
    else:
        if logger:
            logger.error("Error obtaining version information from Lax" + str(status_code))
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

def published_considering_poa_status(article_id, settings, is_poa, was_ever_poa):
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
    if ((is_poa is True and was_ever_poa is True) or
        (is_poa is False and was_ever_poa is False)):
        # In this case, any version is sufficient
        if poa_status or vor_status:
            return True
    elif is_poa is False and was_ever_poa is True:
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


def prepare_action_message(settings, article_id, run, expanded_folder, version,
                           status, action, force=False, run_type=None):
        xml_bucket = settings.publishing_buckets_prefix + settings.expanded_bucket
        xml_file_name = get_xml_file_name(settings, expanded_folder, xml_bucket)
        xml_path = 'https://s3-external-1.amazonaws.com/' + xml_bucket + '/' + expanded_folder + '/' + xml_file_name
        carry_over_data = {
            'action': action,
            'location': xml_path,
            'id': article_id,
            'version': int(version),
            'force': force,
            'token': lax_token(run, version, expanded_folder, status, force, run_type)
        }
        message = carry_over_data
        return message


def get_xml_file_name(settings, expanded_folder, xml_bucket, version=None):
    Article = article.article()
    xml_file_name = Article.get_xml_file_name(settings, expanded_folder, xml_bucket, version)
    return xml_file_name


def lax_token(run, version, expanded_folder, status, force=False, run_type=None):
    token = {
        'run': run, 
        'version': version,
        'expanded_folder': expanded_folder,
        'status': status,
        'force': force,
        'run_type': run_type
    }
    return base64_encode_string(json.dumps(token))


def message_from_lax(data):
    """
    format a message from a Lax response data
    """
    return data.get('message') if data.get('message') else '(empty message)'
