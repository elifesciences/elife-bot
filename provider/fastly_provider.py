import requests

class Purge:
    def __init__(self, fastly_api_key):
        self._fastly_api_key = fastly_api_key

    def of_key(self, surrogate_key, service_id):
        url = "https://api.fastly.com/service/%s/purge/%s" % (service_id, surrogate_key)

        response = requests.post(url, headers={
            'Accept': 'application/json',
            'Fastly-Key': self._fastly_api_key,
        })
        response.raise_for_status()
        return response

KEYS = ['articles/{article_id}v{version}', 'articles/{article_id}/videos']

def purge(article_id, version, settings):
    p = Purge(settings.fastly_api_key)
    for service_id in settings.fastly_service_ids:
        for key in KEYS:
            surrogate_key = key.format(article_id=article_id.zfill(5), version=version)
            p.of_key(surrogate_key, service_id)
