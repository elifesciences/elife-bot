import provider.utils as utils


class S3NotificationInfo:
    def __init__(self, event_name, event_time, bucket_name, file_name, file_etag, file_size):
        self.event_name = event_name
        self.event_time = event_time
        self.bucket_name = bucket_name
        self.file_name = file_name
        self.file_etag = file_etag
        self.file_size = file_size

    @staticmethod
    def from_S3SQSMessage(message):
        return S3NotificationInfo(message.event_name(), message.event_time(), message.bucket_name(), message.file_name(),
                              message.file_etag(), message.file_size())

    @staticmethod
    def from_dict(d):
        return S3NotificationInfo(d['event_name'], d['event_time'], d['bucket_name'], d['file_name'], d['file_etag'],
                                  d['file_size'])

    def to_dict(self):
        return {
            'event_name': self.event_name,
            'event_time': self.event_time,
            'bucket_name': self.bucket_name,
            'file_name': self.file_name,
            'file_etag': self.file_etag,
            'file_size': self.file_size
        }


def parse_activity_data(data):
    "parse activity data from an S3 notification into useful bucket and file values"
    info = S3NotificationInfo.from_dict(data)
    filename = info.file_name[info.file_name.rfind('/')+1:]
    bucket_name = info.bucket_name
    bucket_folder = None
    if filename:
        bucket_folder = info.file_name.split(filename)[0]
    # replace + with spaces if present into a real_filename
    real_filename = utils.unquote_plus(filename)
    return real_filename, bucket_name, bucket_folder
