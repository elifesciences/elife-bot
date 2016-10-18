import activity
import json
import boto.sqs
from boto.sqs.message import RawMessage
import provider.lax_provider as lax_provider
from provider.execution_context import Session


class activity_IngestPublishToLax(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "IngestPublishToLax"
        self.pretty_name = "Ingest and Publish To Lax"
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

        session = Session(self.settings)
        data = self.map_data(data, session, data["run"])

        queue_connection_settings = {"sqs_region": self.settings.sqs_region,
                                     "aws_access_key_id":self.settings.aws_access_key_id,
                                     "aws_secret_access_key": self.settings.aws_secret_access_key}

        (message, queue, start_event,
         end_event, end_event_details, exception) = self.get_message_queue(data)

        self.emit_monitor_event(*start_event)

        if end_event == "error":
            self.logger.exception("Exception when Preparing Ingest for Lax. Details: %s", exception)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        self.write_message(queue_connection_settings, queue, message)
        self.emit_monitor_event(*end_event_details)

        return activity.activity.ACTIVITY_SUCCESS

    def get_message_queue(self, data):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))
        try:

            start_event = [self.settings, data['article_id'], data['version'], data['run'], self.pretty_name, "start",
                           "Starting preparation of article for Lax " + data['article_id']]

            message = lax_provider.prepare_action_message(self.settings,
                                                          data['article_id'],
                                                          data['run'],
                                                          data['expanded_folder'],
                                                          data['version'],
                                                          data['status'],
                                                          data['eif_location'],
                                                          'ingest+publish')

            return (message, self.settings.xml_info_queue, start_event, "end",
                    [self.settings, data['article_id'], data['version'], data['run'], self.pretty_name, "end",
                     "Finished preparation of article for Lax. Ingest+Publish sent to Lax" + data['article_id']], None)

        except Exception as e:
            self.logger.exception("Exception when Preparing Ingest+Publish for Lax")
            return (None, None, start_event, "error",
                    [self.settings, data['article_id'], data['version'], data['run'], self.pretty_name, "error",
                     "Error preparing or sending message to lax" + data['article_id'] +
                     " message: " + str(e.message)],
                    str(e.message))

    def write_message(self, connexion_settings, queue, message_data):

        sqs_conn = boto.sqs.connect_to_region(
                        connexion_settings["sqs_region"],
                        aws_access_key_id=connexion_settings["aws_access_key_id"],
                        aws_secret_access_key=connexion_settings["aws_secret_access_key"])

        m = RawMessage()
        m.set_body(json.dumps(message_data))
        output_queue = sqs_conn.get_queue(queue)
        output_queue.write(m)

    def map_data(self, data, session, run):

        data['version'] = session.get_value(run, 'version')
        data['article_id'] = session.get_value(run, 'article_id')
        data['status'] = session.get_value(run, 'status')
        data['expanded_folder'] = session.get_value(run, 'expanded_folder')
        data['update_date'] = session.get_value(run, 'update_date')
        eif_location =  session.get_value(run, 'eif_filename')
        data['eif_location'] = "" if eif_location is None else eif_location
        return data
