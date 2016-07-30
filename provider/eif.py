import arrow
import json
import datetime
from boto.s3.key import Key

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

def add_update_date_to_json(eif_json, update_date, logger=None, eif_filename=None):
    """
    Update date is a string e.g. 2012-10-15T00:00:00Z format
    We want to add update: YYYY-MM-DD to the json
    xml_filename is just for logging purposes
    """
    try:
        updated_date = datetime.datetime.strptime(update_date, "%Y-%m-%dT%H:%M:%SZ")
        update_date_string = updated_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        eif_json['update'] = update_date_string
    except:
        if logger:
            logger.error("Unable to set the update date in the json %s" %
                              str(eif_filename))
    return eif_json

def read_eif_from_s3(conn, bucket_name, eif_filename):
    bucket = conn.get_bucket(bucket_name)
    key = Key(bucket)
    key.key = eif_filename
    json_input = key.get_contents_as_string()
    data = json.loads(json_input)
    return data

def write_eif_to_s3(conn, data, bucket_name, eif_filename):
    json_output = json.dumps(data)
    output_path = eif_filename
    destination = conn.get_bucket(bucket_name)
    destination_key = Key(destination)
    destination_key.key = output_path
    destination_key.set_contents_from_string(json_output)
