import requests


class ShortRetryException(RuntimeError):
    pass


def endpoint(settings, iiif_path_for_article, figure):
    iiif_path_for_figure = iiif_path_for_article.replace("{article_fig}", figure)
    return settings.path_to_iiif_server + iiif_path_for_figure


def try_endpoint(endpoint_uri, logger):
    try:
        response = requests.head(endpoint_uri)
        if response.status_code == 504:
            raise ShortRetryException("Response code was %s" % response.status_code)
        if response.status_code == 404:
            raise ShortRetryException("Response code was %s" % response.status_code)
        if response.status_code != 200:
            logger.error(
                "Error status code != 200. Status code: %s for URL %s\nContent:\n%s",
                response.status_code,
                endpoint_uri,
                response.content,
            )
            return False, endpoint_uri
        return True, endpoint_uri
    except ShortRetryException as e:
        logger.info("short retry because %s", e)
        return try_endpoint(endpoint_uri, logger)
    except Exception as e:
        logger.exception(str(e))
        return False, endpoint_uri
