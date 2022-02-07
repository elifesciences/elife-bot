import json
import uuid
import boto3
from provider.utils import unicode_encode


def send_message(message, settings):

    sns_client = boto3.client(
        "sns",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.sqs_region,
    )

    payload = unicode_encode(json.dumps(message))
    sns_client.publish(TopicArn=settings.event_monitor_topic, Message=payload)


def build_event_message(
    item_identifier, version, run, event_type, timestamp, status, message
):
    message = {
        "message_type": "event",
        "item_identifier": item_identifier,
        "version": version,
        "run": run,
        "event_type": event_type,
        "timestamp": timestamp.isoformat(),
        "status": status,
        "message": message,
        "message_id": str(uuid.uuid4()),
    }
    return message


def build_property_message(item_identifier, version, name, value, property_type):
    message = {
        "message_type": "property",
        "item_identifier": item_identifier,
        "version": version,
        "name": name,
        "value": value,
        "property_type": property_type,
        "message_id": str(uuid.uuid4()),
    }
    return message
