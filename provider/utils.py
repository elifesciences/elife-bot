import re

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
