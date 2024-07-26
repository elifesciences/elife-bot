import os
import requests

REQUESTS_TIMEOUT = (10, 60)

# MECA file name configuration
MECA_FILE_NAME_PATTERN = "{article_id}-v{version}-meca.zip"

# path in the bucket to a MECA file
MECA_BUCKET_FOLDER = "/reviewed-preprints/"


def meca_file_name(article_id, version):
    "name for a MECA zip file"
    return MECA_FILE_NAME_PATTERN.format(article_id=article_id, version=version)


def post_xml_file(file_path, endpoint_url, user_agent, caller_name, logger):
    "POST the file_path to the XSLT endpoint"
    headers = None
    if user_agent:
        headers = {"user-agent": user_agent}
    file_name = file_path.split(os.sep)[-1]
    files = []
    logger.info(
        "%s, request to endpoint: POST file %s to %s",
        (caller_name, file_path, endpoint_url),
    )
    response = None
    with open(file_path, "rb") as open_file:
        files.append(("file", (file_name, open_file, "text/xml")))
        response = requests.post(
            endpoint_url, timeout=REQUESTS_TIMEOUT, headers=headers, files=files
        )
    if response and response.status_code not in [200]:
        raise Exception(
            "%s, error posting file %s to endpoint %s: %s, %s"
            % (
                caller_name,
                file_path,
                endpoint_url,
                response.status_code,
                response.content,
            )
        )
    if response and response.status_code == 200:
        return response.content
    return None


def post_to_endpoint(xml_file_path, endpoint_url, user_agent, caller_name, logger):
    "post XML file to endpoint, catch exceptions, return response content"
    try:
        response_content = post_xml_file(
            xml_file_path,
            endpoint_url,
            user_agent,
            caller_name,
            logger,
        )
    except Exception as exception:
        logger.exception(
            "%s, posting %s to endpoint %s: %s"
            % (
                caller_name,
                xml_file_path,
                endpoint_url,
                str(exception),
            )
        )
        response_content = None
    return response_content


def log_to_session(log_message, session):
    "save the message to the session"
    # add the log_message to the session variable
    log_messages = session.get_value("log_messages")
    if log_messages is None:
        log_messages = log_message
    else:
        log_messages += log_message
    session.store_value("log_messages", log_messages)
