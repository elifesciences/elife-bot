import arrow

def extract_update_date(data_json, response_json):
    """
    Given passthrough data and response data, both in json format
    choose which should provide the update_date or update value
    """
    update_date = None
    if data_json.get("update_date"):
        update_date = data_json.get("update_date")
    else:
        update = response_json.get('update')
        if update:
            try:
                arrow_date = arrow.get(update, "YYYY-MM-DDTHH:mm:ssZZ")
                update_date = arrow_date.to('utc').format("YYYY-MM-DDTHH:mm:ss") + "Z"
            except arrow.parser.ParserError:
                pass

    return update_date