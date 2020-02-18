from collections import OrderedDict
import requests
from requests.exceptions import HTTPError


def jats_post_params(api_key, account_key):
    """the full endpoint URL to authenticate via URL parameters"""
    params = OrderedDict()
    params["apiKey"] = api_key
    params["accountKey"] = account_key
    return params


def jats_post_payload(content_type, doi, jats_content, api_key, account_key):
    """compile the POST data payload"""
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


def post_as_data(url, payload, params=None):
    """post the payload as form data"""
    return requests.post(url, data=payload, params=params)


def post_as_json(url, payload):
    """post the payload as JSON data"""
    return requests.post(url, json=payload)


def post_to_endpoint(url, payload, logger, identifier, params=None):
    """issue the POST"""
    try:
        resp = post_as_data(url, payload, params=params)
    except:
        logger.exception('Exception in post_to_endpoint')
        raise

    # Check for good HTTP status code
    if resp.status_code != 200:
        response_error_message = (
            "Error posting %s to endpoint %s: status_code: %s\nresponse: %s" %
            (identifier, url, resp.status_code, resp.content))
        full_error_message = (
            "%s\npayload: %s" %
            (response_error_message, payload))
        logger.error(full_error_message)
        raise HTTPError(response_error_message)
    logger.info(
        ("Success posting %s to endpoint %s: status_code: %s\nresponse: %s" +
         " \npayload: %s") %
        (identifier, url, resp.status_code, resp.content, payload))


def success_email_subject_doi(identity, doi):
    """email subject for a success email"""
    return u'{identity}JATS posted for article {doi}'.format(
        identity=identity,
        doi=str(doi))


def success_email_subject_msid_author(identity, msid, author):
    """email subject for a success email with msid and author values"""
    return u'{identity}JATS posted for article {msid:0>5}, author {author}'.format(
        identity=identity,
        msid=str(msid),
        author=author)


def success_email_body_content(doi, jats_content):
    """
    Format the body content of the email
    """
    return "JATS content for article %s:\n\n%s\n\n" % (doi, jats_content)


def error_email_subject_doi(identity, doi):
    """email subject for an error email"""
    return u'Error in {identity} JATS post for article {doi}'.format(
        identity=identity,
        doi=str(doi))


def error_email_subject_msid_author(identity, msid, author):
    """email subject for an error email with msid and author values"""
    return u'Error in {identity} JATS post for article {msid:0>5}, author {author}'.format(
        identity=identity,
        msid=str(msid),
        author=author)


def error_email_body_content(doi, jats_content, error_messages):
    """body content of an error email"""
    content = ""
    if error_messages:
        content += str(error_messages)
        content += "\n\nMore details about the error may be found in the worker.log file\n\n"
    if doi:
        content += "Article DOI: %s\n\n" % doi
    content += "JATS content: %s\n\n" % jats_content
    return content
