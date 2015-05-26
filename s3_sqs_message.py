from boto.sqs.message import Message
import json

class S3SQSMessage(Message):
    def __init__(self, queue=None, body='', xml_attrs=None):
        Message.__init__(self, queue, body)
        self.payload = None

    def file_   name(self):
        return self.payload['Records'][0]['s3']['object']['key']

    def bucket_name(self):
        return self.payload['Records'][0]['s3']['bucket']['name']

    def set_body(self, body):
        """
        Override set_body to construct json payload
        Note Boto JSONMessage seemed to have encoding issues with S3 notification messages
        """
        if body is not None and len(body) > 0:
            self.payload = json.loads(body)
        super(Message, self).set_body(body)


