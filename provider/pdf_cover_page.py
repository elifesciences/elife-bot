import requests
from provider.utils import pad_msid


def get_pdf_cover_link(pdf_cover_generator_url, doi_id, logger):

    url = pdf_cover_generator_url + pad_msid(doi_id)
    logger.info("URL for PDF Generator %s", url)
    resp = requests.post(url)
    logger.info("Response code for PDF Generator %s", str(resp.status_code))
    assert (
        resp.status_code != 404
    ), "PDF cover not found. Format: %s - url requested: %s" % (format, url)
    assert resp.status_code in [200, 202], (
        "unhandled status code from PDF cover service: %s . "
        "Format: %s - url requested: %s" % (resp.status_code, format, url)
    )
    data = resp.json()
    logger.info("PDF Generator Response %s", str(data))
    return data["formats"]


def get_pdf_cover_page(doi_id, settings, logger):
    try:
        assert hasattr(
            settings, "pdf_cover_landing_page"
        ), "pdf_cover_landing_page variable is missing from settings file!"
        return settings.pdf_cover_landing_page + doi_id
    except AssertionError as err:
        logger.error(str(err))
        return ""
