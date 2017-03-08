import requests

def endpoint(settings, iiif_path_for_article, figure):
    iiif_path_for_figure = iiif_path_for_article.replace('{article_fig}', figure)
    return settings.path_to_iiif_server + iiif_path_for_figure

def try_endpoint(endpoint, logger):
    try:
        response = requests.head(endpoint)
        if response.status_code != 200:
            logger.error("Error status code != 200. Status code: " + str(response.status_code) + " for URL: " + endpoint)
            return False, endpoint
        return True, endpoint
    except Exception as e:
        logger.exception(str(e))
        return False, endpoint