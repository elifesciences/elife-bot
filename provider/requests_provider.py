from collections import OrderedDict
import requests


def jats_post_payload(content_type, doi, jats_content, api_key):
    """compile the POST data payload"""
    account_key = 1
    payload = OrderedDict()
    payload["apiKey"] = api_key
    payload["accountKey"] = account_key
    payload["doi"] = doi
    payload["type"] = content_type
    payload["content"] = jats_content
    return payload


def get_as_params(url, payload):
    """transmit the payload as a GET with URL parameters"""
    return requests.get(url, params=payload)


def post_as_params(url, payload):
    """post the payload as URL parameters"""
    return requests.post(url, params=payload)


def post_as_data(url, payload):
    """post the payload as form data"""
    return requests.post(url, data=payload)


def post_as_json(url, payload):
    """post the payload as JSON data"""
    return requests.post(url, json=payload)


def post_to_endpoint(url, payload, logger, identifier):
    """issue the POST"""
    resp = post_as_data(url, payload)
    # Check for good HTTP status code
    if resp.status_code != 200:
        response_error_message = (
            "Error posting %s to endpoint %s: status_code: %s\nresponse: %s" %
            (identifier, url, resp.status_code, resp.content))
        full_error_message = (
            "%s\npayload: %s" %
            (response_error_message, payload))
        logger.error(full_error_message)
        return response_error_message
    logger.info(
        ("Success posting %s to endpoint %s: status_code: %s\nresponse: %s" +
         " \npayload: %s") %
        (identifier, url, resp.status_code, resp.content, payload))
    return True
