import re
import urllib
import base64
import arrow
from argparse import ArgumentParser


S3_DATE_FORMAT = '%Y%m%d%H%M%S'
PUB_DATE_FORMAT = "%Y-%m-%d"
DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def pad_msid(msid):
    return '{:05d}'.format(int(msid))

def pad_volume(volume):
    return '{:02d}'.format(int(volume))

def tidy_whitespace(string):
    string = re.sub('\n', ' ', string)
    string = re.sub(' +', ' ', string)
    string = string.strip()
    return string

def article_status(is_poa):
    return 'POA' if is_poa else 'VOR'

def msid_from_doi(doi):
    "return just the id portion of the doi"
    try:
        msid = int(doi.split(".")[-1])
    except:
        msid = None
    return msid

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
        bytes_string = bytes_string.decode('utf8')
    except (UnicodeEncodeError, AttributeError):
        pass
    return bytes_string


def base64_encode_string(string):
    "base64 endcode string for python 3"
    return base64.encodebytes(bytes(string, 'utf8')).decode()


def base64_decode_string(string):
    "base64 decode string for python 3"
    return base64.decodebytes(bytes(string, 'utf8')).decode()


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


def console_start_env():
    """capture ENV from arguments when running standalone"""
    parser = ArgumentParser()
    parser.add_argument("-e", "--env", default="dev", action="store", type=str, dest="env",
                        help="set the environment to run, either dev or live")
    args, unknown = parser.parse_known_args()
    return args.env


def get_settings(env):
    """for runtime importing of settings module"""
    import settings as settings_lib
    return settings_lib.get_settings(env)
