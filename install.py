import boto.s3
from boto.s3.connection import S3Connection
from boto import sqs
import boto3
import settings as settingsLib
import sys
import json

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s environment-name\n" % sys.argv[0])
        sys.exit(1)
    env = sys.argv[1]
    if env not in ['end2end']:
        print("The environment %s does not specify the bucket names in a consistent way. If it does, whitelist it here")
        sys.exit(2)
    settings = settingsLib.get_settings(env)
    s3_conn = S3Connection(settings.aws_access_key_id, settings.aws_secret_access_key)
    def normalize(name):
        if not name.startswith(settings.publishing_buckets_prefix):
            name = settings.publishing_buckets_prefix + name
        return name
    def filter_keys_containing(clue, settings):
        return { key:normalize(name) for key,name in settings.__dict__.iteritems() if clue in key }
    buckets_to_create = filter_keys_containing("bucket", settings)
    del buckets_to_create['publishing_buckets_prefix']

    for bucket in buckets_to_create.values():
        print("Creating bucket %s..." % bucket)
        #s3_conn.create_bucket(bucket)
        print("Created bucket %s" % bucket)

    sqs_conn = boto.sqs.connect_to_region("us-east-1", aws_access_key_id=settings.aws_access_key_id, aws_secret_access_key=settings.aws_secret_access_key)
    queues_to_create = [settings.S3_monitor_queue, settings.event_monitor_queue, settings.workflow_starter_queue]
    for queue in queues_to_create:
        print("Creating queue %s..." % queue)
        sqs_conn.create_queue(queue, 60)
        print("Created queue %s" % queue)

    print(settings.S3_monitor_queue)
    # needs to have a policy allowing S3 to write to it
    S3_monitor_queue = sqs_conn.get_queue(settings.S3_monitor_queue)
    # this sets up a single permission for everyone in the AWS account
    # to write to this queue. Finer permissions are refused by the API,


    # this one is too general, and fails when we add the event notification to the bucket
    #sqs_conn.add_permission(S3_monitor_queue, "%s%sSendMessage" % (settings.publishing_buckets_prefix, settings.production_bucket), 512686554592, 'SendMessage')
    # this one doesn't work, 400 Bad Request without explanation of what is the problem
    '''
    resource = "arn:aws:sqs:us-east-1:512686554592:%s" % settings.S3_monitor_queue
    policy = json.dumps({
         'Version': '2016-05-26',
         'Id': resource + '/SQSDefaultPolicy',
         'Statement': [
                {
                        'Sid': 'Sid1464267862599',
                        'Effect': 'Allow',
                        'Principal': '*',
                        'Action': 'SQS:SendMessage',
                        "Resource": resource,
                        'Condition': {
                            'StringLike': {
                                'aws:SourceArn': 'arn:aws:s3:*:*:%s' % settings.publishing_buckets_prefix + settings.production_bucket
                                }
                            }
                    }
            ]
    })
    print(policy)
    sqs_conn.set_queue_attribute(S3_monitor_queue, 'Policy', policy)
    '''

    # needs the S3 bucket settings.production_bucket to send the notification
    # we have to use boto3 because boto (2.x) cannot do this
    production_bucket = settings.publishing_buckets_prefix + settings.production_bucket
    s3 = boto3.resource('s3', aws_access_key_id=settings.aws_access_key_id, aws_secret_access_key=settings.aws_secret_access_key)
    bucket_notification = s3.BucketNotification(production_bucket)
    response = bucket_notification.put( NotificationConfiguration={
        'QueueConfigurations': [
            {
                'QueueArn': S3_monitor_queue.arn,
                'Events': [
                    's3:ObjectCreated:*',
                    ],
                },
            ],
    })

    # SWF
    swf = boto3.client('swf', aws_access_key_id=settings.aws_access_key_id, aws_secret_access_key=settings.aws_secret_access_key, region_name='us-east-1')
    print("Checking SWF domain %s" % settings.domain)
    list_domain_response = swf.list_domains(
        registrationStatus='REGISTERED',
        maximumPageSize=100
    )
    domains = [ d['name'] for d in list_domain_response['domainInfos'] ]
    if settings.domain not in domains:
        swf.register_domain(name=settings.domain, description="%s SWF domain" % env, workflowExecutionRetentionPeriodInDays="90")
    print("SWF domain %s is now present" % settings.domain)

