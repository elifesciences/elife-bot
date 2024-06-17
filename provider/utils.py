import datetime
import os
import re
import urllib
import base64
from xml.dom import minidom
from xml.etree import ElementTree
from argparse import ArgumentParser
import arrow
from mimetypes import guess_type
from elifetools import utils as etoolsutils
import boto3
from functools import partial

S3_DATE_FORMAT = "%Y%m%d%H%M%S"
PUB_DATE_FORMAT = "%Y-%m-%d"
DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def pad_msid(msid):
    return "{:05d}".format(int(msid))


def pad_volume(volume):
    return "{:02d}".format(int(volume))


def tidy_whitespace(string):
    string = re.sub("\n", " ", string)
    string = re.sub(" +", " ", string)
    string = string.strip()
    return string


def article_status(is_poa):
    return "POA" if is_poa else "VOR"


def msid_from_doi(doi):
    "return just the article id portion of an eLife doi as an integer"
    if not doi:
        return
    if not isinstance(doi, str):
        return
    regex = r"10\.7554/elife\.(?P<msid>\d+)"
    match_list = re.findall(regex, doi, re.IGNORECASE)
    if len(match_list) > 0:
        return int(match_list[0])


def volume_from_year(year, start_year=2011):
    "calculate the volume from the year, default start_year value for elife journal"
    try:
        volume = int(year) - start_year
    except:
        volume = None
    return volume


def volume_from_pub_date(pub_date, start_year=2011):
    "calculate the volume from a time.struct_time, default start_year value for elife journal"
    try:
        volume = volume_from_year(pub_date[0], start_year)
    except:
        volume = None
    return volume


def unquote_plus(string):
    "unescape plus sign url in python 3"
    if not string:
        return string
    # python 3
    return urllib.parse.unquote_plus(string)


def bytes_decode(bytes_string):
    "try to decode to utf8"
    try:
        bytes_string = bytes_string.decode("utf8")
    except (UnicodeEncodeError, AttributeError):
        pass
    return bytes_string


def base64_encode_string(string):
    "base64 endcode string for python 3"
    return base64.encodebytes(bytes(string, "utf8")).decode()


def base64_decode_string(string):
    "base64 decode string for python 3"
    return base64.decodebytes(bytes(string, "utf8")).decode()


def unicode_encode(string):
    """safely encode string as utf8 by catching exceptions"""
    if string is None or isinstance(string, str):
        return string
    # decode bytes to string
    return bytes_decode(string)


def set_datestamp(glue=""):
    arrow_date = arrow.utcnow()
    date_stamp = glue.join(
        [
            str(arrow_date.datetime.year),
            str(arrow_date.datetime.month).zfill(2),
            str(arrow_date.datetime.day).zfill(2),
        ]
    )
    return date_stamp


def get_current_datetime():
    "for easier mocking in tests wrap this call"
    return datetime.datetime.now(datetime.timezone.utc)


def utctimestamp(dt):
    "get a timestamp for utc timezone from a datetime object"
    return dt.replace(tzinfo=datetime.timezone.utc).timestamp()


def get_activity_status_text(activity_status):
    """
    Given the activity status boolean, return a human
    readable text version
    """
    if activity_status is True:
        activity_status_text = "Success!"
    else:
        activity_status_text = "FAILED."

    return activity_status_text


def get_doi_url(doi):
    """
    Given a DOI, get the URL for the DOI
    """
    return "https://doi.org/%s" % doi


def doi_uri_to_doi(doi_url):
    "get the DOI portion of a DOI URL"
    return etoolsutils.doi_uri_to_doi(doi_url)


def version_doi_parts(version_doi):
    """
    split version DOI into the concept DOI and version number
    e.g. 10.7554/eLife.84364.2 return 10.7554/eLife.84364, 1
    """
    return version_doi.rsplit(".", 1)


def element_xml_string(element, pretty=False, indent=""):
    "generate string XML output from an Element object"
    encoding = "utf-8"
    rough_string = ElementTree.tostring(element, encoding)
    reparsed = minidom.parseString(rough_string)

    if pretty is True:
        return reparsed.toprettyxml(indent, encoding=encoding)
    return reparsed.toxml(encoding=encoding)


CONSOLE_ARGUMENT_MAP = {
    "e": {
        "flags": ["-e", "--env"],
        "default": "dev",
        "action": "store",
        "type": str,
        "dest": "env",
        "help": "set the environment to run, either dev or live",
    },
    "d": {
        "flags": ["-d", "--doi-id"],
        "default": None,
        "action": "store",
        "type": str,
        "dest": "doi_id",
        "help": "specify the DOI id of a single article",
    },
    "w": {
        "flags": ["-w", "--workflow-name"],
        "default": None,
        "action": "store",
        "type": str,
        "dest": "workflow",
        "help": "specify the workflow name to start",
    },
    "f": {
        "flags": ["-f", "--file"],
        "default": None,
        "action": "store",
        "type": str,
        "dest": "document",
        "help": "specify the S3 object name of the input file",
    },
}


def settings_environment(settings_object):
    "get the environment name from the settings object class name"
    if not callable(settings_object):
        return None
    return type(settings_object()).__name__


def add_console_argument(parser, argument_name):
    details = CONSOLE_ARGUMENT_MAP.get(argument_name)
    if details:
        parser.add_argument(
            *details.get("flags"),
            default=details.get("default"),
            action=details.get("action"),
            type=details.get("type"),
            dest=details.get("dest"),
            help=details.get("help")
        )


def console_start_env():
    """capture ENV from arguments when running standalone"""
    parser = ArgumentParser()
    add_console_argument(parser, "e")
    args, unknown = parser.parse_known_args()
    return args.env


def console_start_env_doi_id():
    """capture ENV and DOI_ID from arguments when running standalone"""
    parser = ArgumentParser()
    add_console_argument(parser, "e")
    add_console_argument(parser, "d")
    args, unknown = parser.parse_known_args()
    return args.env, args.doi_id


def console_start_env_document():
    """capture ENV and DOCUMENT from arguments when running standalone"""
    parser = ArgumentParser()
    add_console_argument(parser, "e")
    add_console_argument(parser, "f")
    args, unknown = parser.parse_known_args()
    return args.env, args.document


def console_start_env_workflow():
    """capture ENV, WORKFLOW from arguments when running standalone"""
    parser = ArgumentParser()
    add_console_argument(parser, "e")
    add_console_argument(parser, "w")
    args, unknown = parser.parse_known_args()
    return args.env, args.workflow


def console_start_env_workflow_doi_id():
    """capture ENV, WORKFLOW, and DOI_ID from arguments when running standalone"""
    parser = ArgumentParser()
    add_console_argument(parser, "e")
    add_console_argument(parser, "d")
    add_console_argument(parser, "w")
    args, unknown = parser.parse_known_args()
    return args.env, args.doi_id, args.workflow


def create_aws_connection(service, service_creation_kwargs):
    assert isinstance(service, str), "`service` must be a string"
    assert isinstance(
        service_creation_kwargs, dict
    ), "`service_creation_kwargs` must be a dictionary"

    return boto3.client(service, **service_creation_kwargs)


def get_aws_connection_key(service, service_creation_kwargs):
    "returns a tuple for the given `service` that can be used in a dictionary"
    kv = service_creation_kwargs
    # ('s3', 'us-east-1', '1234567890', Config{...})
    return (
        service,
        kv.get("region_name"),
        kv.get("aws_access_key_id"),
        kv.get("config"),
    )


def get_aws_connection(service_conn_map, service, service_creation_kwargs):
    "centralised access to AWS service connections"
    assert isinstance(service_conn_map, dict), "`service_conn_map` must be a dictionary"
    assert isinstance(service, str), "`service` must be a string"
    assert isinstance(
        service_creation_kwargs, dict
    ), "`service_creation_kwargs` must be a dictionary"

    if service in service_conn_map:
        return service_conn_map[service]

    map_key = get_aws_connection_key(service, service_creation_kwargs)

    service_conn_map[map_key] = create_aws_connection(service, service_creation_kwargs)
    return service_conn_map[map_key]


def get_settings(env):
    """for runtime importing of settings module"""
    import settings as settings_lib

    settings_inst = settings_lib.get_settings(env)

    settings_inst._aws_conn_map = {}
    settings_inst.aws_conn = partial(get_aws_connection, settings_inst._aws_conn_map)

    return settings_inst


def content_type_from_file_name(file_name):
    "for setting Content-Type headers on S3 objects, for example"
    if file_name is None:
        return None
    content_type, encoding = guess_type(file_name)
    if content_type is None:
        return "binary/octet-stream"
    else:
        return content_type


ENVVAR_KNOWN_KEYS = {
    "MOTO_ALLOW_NONEXISTENT_REGION",
    "TEST_DUMMY",
}


def envvar(key, default=None):
    """returns a value for the environment variable `key`.
    raises an `AssertionError` if the requested environment variable is unknown."""
    assert key in ENVVAR_KNOWN_KEYS, (
        "programming error. unsupported environment key: %s" % key
    )
    return os.environ.get(key, default)


def set_envvar(key, val):
    """set a value `val` for the environment variable `key`.
    raises an `AssertionError` if the requested environment variable is unknown."""
    assert key in ENVVAR_KNOWN_KEYS, (
        "programming error. unsupported environment key: %s" % key
    )
    os.environ[key] = val
