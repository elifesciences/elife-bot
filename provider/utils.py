
S3_DATE_FORMAT = '%Y%m%d%H%M%S'

def pad_msid(msid):
    return '{:05d}'.format(int(msid))

def pad_volume(volume):
    return '{:02d}'.format(int(volume))
