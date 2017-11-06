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
