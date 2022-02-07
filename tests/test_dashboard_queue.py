import unittest
import datetime
from mock import patch
import dashboard_queue


class TestDashboardQueue(unittest.TestCase):
    @patch("uuid.uuid4")
    def test_build_event_message(self, fake_uuid4):
        fake_uuid4.return_value = "uuid"
        now = datetime.datetime.now()
        item_identifier = "00666"
        version = "1"
        run = "run"
        event_type = "PingWorker"
        status = "start"
        message = "Started PingWorker"
        message_returned = dashboard_queue.build_event_message(
            item_identifier, version, run, event_type, now, status, message
        )
        expected = {
            "message_type": "event",
            "item_identifier": item_identifier,
            "version": version,
            "run": run,
            "event_type": event_type,
            "timestamp": now.isoformat(),
            "status": status,
            "message": message,
            "message_id": "uuid",
        }
        self.assertDictEqual(message_returned, expected)

    def test_build_event_message_timestamp_exception(self):
        """
        test an unacceptable timestamp value:
        AttributeError: 'str' object has no attribute 'isoformat'
        """
        with self.assertRaises(AttributeError):
            dashboard_queue.build_event_message(
                item_identifier="",
                version="",
                run="",
                event_type="",
                timestamp="",
                status="",
                message="",
            )

    @patch("uuid.uuid4")
    def test_build_property_message(self, fake_uuid4):
        fake_uuid4.return_value = "uuid"
        item_identifier = "00666"
        version = "1"
        name = "publication-status"
        value = "ready to publish"
        property_type = "text"
        message_returned = dashboard_queue.build_property_message(
            item_identifier, version, name, value, property_type
        )
        expected = {
            "message_type": "property",
            "item_identifier": item_identifier,
            "version": version,
            "name": name,
            "value": value,
            "property_type": property_type,
            "message_id": "uuid",
        }

        self.assertDictEqual(message_returned, expected)
