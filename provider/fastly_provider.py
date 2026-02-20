import requests
from provider import utils


class FastlyApi:
    def __init__(self, fastly_api_key):
        self._fastly_api_key = fastly_api_key

    def purge(self, surrogate_key, service_id, user_agent=None):
        url = "https://api.fastly.com/service/%s/purge/%s" % (service_id, surrogate_key)
        headers = {
            "Accept": "application/json",
            "Fastly-Key": self._fastly_api_key,
            "Fastly-Soft-Purge": "1",
        }
        if user_agent:
            headers["user-agent"] = user_agent
        response = requests.post(
            url,
            headers=headers,
        )
        response.raise_for_status()
        return response


KEYS = [
    "article/{article_id}v{version}",
    "article/{article_id}/videos",
    "digest/{article_id}",
]


def purge(article_id, version, settings):
    responses = []
    api = FastlyApi(settings.fastly_api_key)
    user_agent = getattr(settings, "user_agent", None)
    for service_id in settings.fastly_service_ids:
        for key in KEYS:
            surrogate_key = key.format(
                article_id=utils.pad_msid(article_id), version=version
            )
            responses.append(api.purge(surrogate_key, service_id, user_agent))

    return responses


PREPRINT_KEYS = [
    "preprint/{article_id}v{version}",
    "preprint/{article_id}",
]


def purge_preprint(article_id, version, settings):
    "purge preprint surrogate keys"
    responses = []
    api = FastlyApi(settings.fastly_api_key)
    for service_id in settings.fastly_service_ids:
        for key in PREPRINT_KEYS:
            surrogate_key = key.format(
                article_id=utils.pad_msid(article_id), version=version
            )
            responses.append(api.purge(surrogate_key, service_id))

    return responses
