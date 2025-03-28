import json
from S3utility.s3_notification_info import S3NotificationInfo


class S3SQSMessage:
    def __init__(self, body=""):
        self.payload = None
        self.notification_type = "S3Info"
        self.set_body(body)

    def event_name(self):
        return self.payload["Records"][0]["eventName"]

    def event_time(self):
        return self.payload["Records"][0]["eventTime"]

    def bucket_name(self):
        return self.payload["Records"][0]["s3"]["bucket"]["name"]

    def file_name(self):
        return self.payload["Records"][0]["s3"]["object"]["key"]

    def file_etag(self):
        if "eTag" in self.payload["Records"][0]["s3"]["object"]:
            return self.payload["Records"][0]["s3"]["object"]["eTag"]
        else:
            return None

    def file_size(self):
        return self.payload["Records"][0]["s3"]["object"]["size"]

    def set_body(self, body):
        """
        Override set_body to construct json payload
        Note Boto JSONMessage seemed to have encoding issues with S3 notification messages
        """
        if body is not None and len(body) > 0:
            self.payload = json.loads(body)
        if body and "Records" in list(self.payload.keys()):
            self.notification_type = "S3Event"
        elif body and "Message" in list(self.payload.keys()):
            self.payload = json.loads(self.payload.get("Message"))
            if "Records" in list(self.payload.keys()):
                self.notification_type = "S3Event"
