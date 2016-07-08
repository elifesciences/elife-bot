import requests
import time

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
        for version in data:
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