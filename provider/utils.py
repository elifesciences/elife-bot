import re
import urllib
import base64
import arrow

S3_DATE_FORMAT = '%Y%m%d%H%M%S'
PUB_DATE_FORMAT = "%Y-%m-%d"

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
    "unescape plus sign url with python 2 or 3 method"
    if not string:
        return string
    if hasattr(urllib, 'parse'):
        # python 3
        return urllib.parse.unquote_plus(string)
    return urllib.unquote_plus(string)


def unicode_decode(string):
    "try to decode from utf8"
    try:
        string = string.decode('utf8')
    except (UnicodeEncodeError, AttributeError):
        pass
    return string


def base64_encode_string(string):
    "base64 endcode string for python 2 or 3"
    if hasattr(base64, 'encodebytes'):
        # python 3
        return base64.encodebytes(bytes(string, 'utf8')).decode()
    return base64.encodestring(string)


def base64_decode_string(string):
    "base64 decode string for python 2 or 3"
    if hasattr(base64, 'decodebytes'):
        # python 3
        return base64.decodebytes(bytes(string, 'utf8')).decode()
    return base64.decodestring(string)


def unicode_encode(string):
    """safely encode string as utf8 by catching exceptions"""
    if string is None or isinstance(string, str):
        return string
    try:
        string = string.encode('utf8')
    except (UnicodeDecodeError, TypeError, AttributeError):
        string = unicode_decode(string)
    return string


def set_datestamp():
    arrow_date = arrow.utcnow()
    date_stamp = (str(arrow_date.datetime.year) + str(arrow_date.datetime.month).zfill(2) +
                  str(arrow_date.datetime.day).zfill(2))
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
