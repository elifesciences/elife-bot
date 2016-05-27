import boto3
import settings as settingsLib

settings = settingsLib.get_settings('end2end')
s3 = boto3.resource('s3', aws_access_key_id = settings.aws_access_key_id, aws_secret_access_key = settings.aws_secret_access_key)
