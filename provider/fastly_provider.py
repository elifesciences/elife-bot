import requests

def purge(article_id, settings):
    surrogate_key = 'articles/%s' % article_id.zfill(5)
    url = "https://api.fastly.com/service/%s/purge/%s" % (settings.fastly_service_id, surrogate_key)

    response = requests.post(url, headers={
        'Accept': 'application/json',
        'Fastly-Key': settings.fastly_api_key
    })
    response.raise_for_status()
    return response
