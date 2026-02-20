import json
import requests


REQUESTS_TIMEOUT = 15

DEFAULT_OPTIONS_JSON = {
    "math_inline_delimiters": ["$", "$"],
    "rm_spaces": True,
    "formats": ["text", "data", "html", "latex_styled"],
    "data_options": {
        "include_mathml": True,
        "include_latex": True,
    },
}

TABLE_OPTIONS_JSON = {
    "math_inline_delimiters": ["$", "$"],
    "rm_spaces": True,
    "formats": ["data"],
    "data_options": {
        "include_table_html": True,
        "include_tsv": True,
    },
    "enable_tables_fallback": True,
}


def mathpix_table_post_request(
    url,
    app_id,
    app_key,
    file_path,
    options_json=None,
    verify_ssl=False,
    logger=None,
    user_agent=None,
):
    "POST to Mathpix API endpoint using table options"
    return mathpix_post_request(
        url,
        app_id,
        app_key,
        file_path,
        options_json=TABLE_OPTIONS_JSON,
        verify_ssl=verify_ssl,
        logger=logger,
        user_agent=user_agent,
    )


def mathpix_post_request(
    url,
    app_id,
    app_key,
    file_path,
    options_json=None,
    verify_ssl=False,
    logger=None,
    user_agent=None,
):
    "POST JSON data to Mathpix API endpoint"

    if options_json is None:
        # use the default options
        options_json = DEFAULT_OPTIONS_JSON

    headers = {"app_id": app_id, "app_key": app_key}
    if user_agent:
        headers["user-agent"] = user_agent
    data = {"options_json": json.dumps(options_json)}
    with open(file_path, "rb") as open_file:
        files = {"file": open_file}
        response = requests.post(
            url,
            files=files,
            data=data,
            verify=verify_ssl,
            headers=headers,
            timeout=REQUESTS_TIMEOUT,
        )
    if logger:
        logger.info("Post file %s to Mathpix API: POST %s\n" % (file_path, url))
        logger.info(
            "Response from Mathpix API: %s\n%s"
            % (response.status_code, response.content)
        )
    status_code = response.status_code
    if not 300 > status_code >= 200:
        raise Exception(
            "Error in mathpix_post_request %s to Mathpix API: %s\n%s"
            % (file_path, status_code, response.content)
        )

    return response
