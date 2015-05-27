from boto.sqs.message import Message
import json
from s3_notification_info import S3NotificationInfo


class S3SQSMessage(Message):
    def __init__(self, queue=None, body='', xml_attrs=None):
        Message.__init__(self, queue, body)
        self.payload = None
        self.notification_type = 'S3Info'

    def event_name(self):
        return self.payload['Records'][0]['eventName']

    def event_time(self):
        return self.payload['Records'][0]['eventTime']

    def bucket_name(self):
        return self.payload['Records'][0]['s3']['bucket']['name']

    def file_name(self):
        return self.payload['Records'][0]['s3']['object']['key']

    def file_etag(self):
        return self.payload['Records'][0]['s3']['object']['eTag']

    def file_size(self):
        return self.payload['Records'][0]['s3']['object']['size']

    def set_body(self, body):
        """
        Override set_body to construct json payload
        Note Boto JSONMessage seemed to have encoding issues with S3 notification messages
        """
        if body is not None and len(body) > 0:
            self.payload = json.loads(body)
        if body and 'Records' in self.payload.keys():
            self.notification_type = 'S3Event'
        super(Message, self).set_body(body)
