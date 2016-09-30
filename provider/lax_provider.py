import requests
import time
from article import article
import base64

def article_versions(article_id, settings):
    url = settings.lax_article_versions.replace('{article_id}', article_id)
    response = requests.get(url, verify=settings.verify_ssl)
    status_code = response.status_code
    data = None
    if status_code == 200:
        data = response.json()
    return status_code, data


def article_highest_version(article_id, settings, logger=None):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        high_version = 0
        for version in data:
            int_version = int(version)
            if int_version > high_version:
                high_version = int_version
        return high_version
    elif status_code == 404:
        return "1"
    else:
        if logger:
            logger.error("Error obtaining version information from Lax" +
                              str(status_code))
        return None


def article_publication_date(article_id, settings, logger=None):
    status_code, data = article_versions(article_id, settings)
    if status_code == 200:
        date_str = None
        for version in data:
            if int(version) == 1:
                article_data = data[version]
                if 'datetime_published' in article_data:

                    try:
                        date_struct = time.strptime(article_data['datetime_published'],
                                                    "%Y-%m-%dT%H:%M:%SZ")
                        date_str = time.strftime('%Y%m%d%H%M%S', date_struct)

                    except:
                        if logger:
                            logger.error("Error parsing the datetime_published from Lax: "
                                         + str(article_data['datetime_published']))

        return date_str
    elif status_code == 404:
        return None
    else:
        if logger:
            logger.error("Error obtaining version information from Lax" + str(status_code))
        return None


def prepare_action_message(settings, article_id, run, expanded_folder, version, status, eif_location, action):
        xml_bucket = settings.publishing_buckets_prefix + settings.expanded_bucket
        Article = article()
        xml_file_name = Article.get_xml_file_name(settings, expanded_folder, xml_bucket)
        xml_path = 'https://s3.amazonaws.com/' + xml_bucket + '/' + expanded_folder + '/' + xml_file_name
        carry_over_data = {
            'action': action,
            'location': xml_path,
            'id': article_id,
            'version': version,
            'token': lax_token(run, version, expanded_folder, status, eif_location)
        }
        message = carry_over_data
        return message

def lax_token(run, version, expanded_folder, status, eif_location):
    raw = '{"run": "' + run + '", ' \
            '"version": "' + version + '", ' \
            '"expanded_folder": "' + expanded_folder + '", ' \
            '"eif_location": "' + eif_location + '", ' \
            '"status": "' + status + '"}'
    return base64.encodestring(raw)

