import boto.sqs
import boto.sns
from boto.sqs.message import Message
import json
import uuid
from provider.utils import unicode_encode


def send_message(message, settings):

    conn = boto.sns.connect_to_region(
        settings.sqs_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    payload = unicode_encode(json.dumps(message))
    conn.publish(topic=settings.event_monitor_topic, message=payload)


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
