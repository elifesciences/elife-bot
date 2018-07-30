"functions shared by digest related activities"
from S3utility.s3_notification_info import S3NotificationInfo
import provider.utils as utils


def parse_data(data):
    info = S3NotificationInfo.from_dict(data)
    filename = info.file_name[info.file_name.rfind('/')+1:]
    bucket_name = info.bucket_name
    bucket_folder = None
    if filename:
        bucket_folder = info.file_name.split(filename)[0]
    # replace + with spaces if present into a real_filename
    real_filename = utils.unquote_plus(filename)
    return real_filename, bucket_name, bucket_folder
