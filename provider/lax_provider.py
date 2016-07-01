import requests

def article_versions(article_id, settings):
    url = settings.lax_article_versions.replace('{article_id}', article_id)
    response = requests.get(url, verify=settings.verify_ssl)
    status_code = response.status_code
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
        return str(high_version + 1)
    elif status_code == 404:
        return "1"
    else:
        if logger:
            logger.error("Error obtaining version information from Lax" +
                              str(status_code))
        return None
