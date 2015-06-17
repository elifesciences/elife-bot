

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
