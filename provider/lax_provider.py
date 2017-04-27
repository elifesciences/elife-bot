import requests
import time
from . import article
import base64
import json
from dateutil.parser import parse
import log
import os

identity = "process_%s" % os.getpid()
logger = log.logger("lax_provider.log", 'INFO', identity)


class ErrorCallingLaxException(Exception):
    pass


def article_versions(article_id, settings):
    url = settings.lax_article_versions.replace('{article_id}', article_id)
    response = requests.get(url, verify=settings.verify_ssl)
    logger.info("Request to lax: GET %s", url)
    logger.info("Response from lax: %s\n%s", response.status_code, response.content)
    status_code = response.status_code
    if status_code not in [200, 404]:
        raise ErrorCallingLaxException("Error looking up article " + article_id + " version in Lax: %s\n%s" % (status_code, response.content))

    if status_code == 200:
        data = response.json()
        if "versions" in data:
            return status_code, data["versions"]

    return status_code, None


def article_highest_version(article_id, settings):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        high_version = 0 if len(data) < 1 else max(map(lambda x: int(x["version"]), data))
        return high_version
    elif status_code == 404:
        return "1"


def article_next_version(article_id, settings):
    version = article_highest_version(article_id, settings)
    if isinstance(version, (int,long)) and version >= 0:
        version = str(version + 1)
    if version is None:
        raise RuntimeError("Error looking up article next version. Version is Null. Check call to Lax.")
    return version


def article_version_date_by_version(article_id, version, settings):
    status_code, data = article_versions(article_id, settings)
    print data
    if status_code == 200:
        version_data = (vd for vd in data if vd["version"] == int(version)).next()
        return parse(version_data["versionDate"]).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise Exception("Error in article_publication_date_by_version: Version date not found. Status: " + str(status_code))


def article_publication_date(article_id, settings, logger=None):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        first_published_version_list = filter(lambda x: int(x["version"]) == 1, data)
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


def prepare_action_message(settings, article_id, run, expanded_folder, version, status, eif_location, action, force=False):
        xml_bucket = settings.publishing_buckets_prefix + settings.expanded_bucket
        xml_file_name = get_xml_file_name(settings, expanded_folder, xml_bucket)
        xml_path = 'https://s3-external-1.amazonaws.com/' + xml_bucket + '/' + expanded_folder + '/' + xml_file_name
        carry_over_data = {
            'action': action,
            'location': xml_path,
            'id': article_id,
            'version': int(version),
            'force': force,
            'token': lax_token(run, version, expanded_folder, status, eif_location, force)
        }
        message = carry_over_data
        return message


def get_xml_file_name(settings, expanded_folder, xml_bucket, version=None):
    Article = article.article()
    xml_file_name = Article.get_xml_file_name(settings, expanded_folder, xml_bucket, version)
    return xml_file_name


def lax_token(run, version, expanded_folder, status, eif_location, force=False):
    token = {
        'run': run, 
        'version': version,
        'expanded_folder': expanded_folder,
        'eif_location': eif_location,
        'status': status,
        'force': force
    }
    return base64.encodestring(json.dumps(token))

