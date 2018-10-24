import base64
from requests.auth import HTTPBasicAuth
import activity
import json
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from provider.execution_context import get_session
import datetime
import boto.sqs
from boto.sqs.message import RawMessage
import provider.lax_provider as lax_provider

"""
activity_IngestToLax.py activity
"""
import requests


class activity_IngestToLax(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "IngestToLax"
        self.pretty_name = "Ingest To Lax"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Prepare data and queue for Lax consumption"
        self.logger = logger

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        run = data["run"]
        session = get_session(self.settings, data, run)
        data['version'] = session.get_value('version')
        data['article_id'] = session.get_value('article_id')
        data['status'] = session.get_value('status')
        data['expanded_folder'] = session.get_value('expanded_folder')
        data['update_date'] = session.get_value('update_date')
        data['run_type'] = session.get_value('run_type')

        queue_connection_settings = {"sqs_region": self.settings.sqs_region,
                                     "aws_access_key_id":self.settings.aws_access_key_id,
                                     "aws_secret_access_key": self.settings.aws_secret_access_key}

        (message, queue, start_event,
         end_event, end_event_details, exception) = self.get_message_queue(data, self.settings.consider_Lax_elife_2_0)

        self.emit_monitor_event(*start_event)
        if end_event == "error":
            self.logger.exception("Exception when Preparing Ingest for Lax. Details: %s", exception)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        self.write_message(queue_connection_settings, queue, message)

        self.emit_monitor_event(*end_event_details)
        return activity.activity.ACTIVITY_SUCCESS



    def get_message_queue(self, data=None, consider_elife_20=True):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        run = data['run']
        version = data['version']
        article_id = data['article_id']
        status = data['status']

        start_event = None
        try:
            expanded_folder = data['expanded_folder']
            run_type = data['run_type']

            ##########
            if not consider_elife_20:

                start_event = [self.settings, article_id, version, run, self.pretty_name + " (Skipping)", "start",
                               "Starting preparation of article " + article_id]

                try:
                    workflow_starter_message = {
                            "workflow_name": "ProcessArticleZip",
                            "workflow_data": {
                                "run":run ,
                                "article_id": article_id,
                                "result": "",
                                "status": status,
                                "version": version,
                                "expanded_folder": expanded_folder,
                                "requested_action": "",
                                "message": "",
                                "update_date": data['update_date'],
                                "run_type": run_type
                            }
                        }

                    return (workflow_starter_message, self.settings.workflow_starter_queue,start_event,
                            "end", [self.settings, article_id, version, run, self.pretty_name + " (Skipping)", "end",
                                    "Lax is not being considered, this activity just triggered next "
                                    "workflow without influence from Lax."], None)

                except Exception as e:
                    return (None, None, start_event, "error",
                            [self.settings, article_id, version, run, self.pretty_name + " (Skipping)", "error",
                             "An error has occurred. Details: %s", str(e.message)],
                            str(e.message))

            ##########

            start_event = [self.settings, article_id, version, run, self.pretty_name, "start",
                           "Starting preparation of article for Lax " + article_id]

            force = True if ("force" in data and data["force"] == True) else False

            message = lax_provider.prepare_action_message(
                self.settings, article_id, run, expanded_folder,
                version, status, 'ingest', force, run_type)

            return (message, self.settings.xml_info_queue, start_event, "end",
                    [self.settings, article_id, version, run, self.pretty_name, "end",
                     "Finished preparation of article for Lax. Ingest sent to Lax" + article_id], None)

        except Exception as e:
            self.logger.exception("Exception when Preparing Ingest for Lax")
            return (None, None, start_event, "error",
                    [self.settings, article_id, version, run, self.pretty_name, "error",
                     "Error preparing or sending message to lax" + article_id +
                     " message: " + str(e.message)],
                    str(e.message))

    def write_message(self, connexion_settings, queue, message_data):
        message_body = json.dumps(message_data)
        self.logger.info("Sending message to lax: %s", message_body)
        sqs_conn = boto.sqs.connect_to_region(
                        connexion_settings["sqs_region"],
                        aws_access_key_id=connexion_settings["aws_access_key_id"],
                        aws_secret_access_key=connexion_settings["aws_secret_access_key"])

        m = RawMessage()
        m.set_body(message_body)
        output_queue = sqs_conn.get_queue(queue)
        output_queue.write(m)
