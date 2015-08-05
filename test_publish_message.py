import boto.sns
import settings as settings_lib
import json

settings = settings_lib.get_settings('exp')
conn = boto.sns.connect_to_region(settings.sqs_region,
                                  aws_access_key_id=settings.aws_access_key_id,
                                  aws_secret_access_key=settings.aws_secret_access_key)

# d = {
#     'workflow_name': "NewS3File",
#     'workflow_data': {
#         'event_name': "S3Event",
#         'event_time': "", 'bucket_name': "xxawsxx-drop-bucket",
#         'file_name': "elife-kitchen-sink.xml", 'file_etag': "3f53f5c808dd58973cd93a368be739b4", 'file_size': 1
#     }
# }

d = {
    'workflow_name': 'ApproveArticlePublication',
    'workflow_data': {
        'article_version_id': '00288.1'
    }
}

conn.publish(topic='arn:aws:sns:eu-west-1:827129359416:workflow-starter-topic', message=json.dumps(d))
