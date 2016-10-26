import activity
from provider.execution_context import Session
from provider.storage_provider import StorageContext
import json

"""
activity_SetEIFPublish.py activity
"""

class activity_SetEIFPublish(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "SetEIFPublish"
        self.pretty_name = "Set EIF Publish"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Sets Publish to True in EIF json in order to publish a silent correction"
        self.logger = logger

    def do_activity(self, data):

        session = Session(self.settings)
        eif_filename = session.get_value(data['run'], 'eif_filename')

        self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                self.pretty_name, "start", "Starting to set EIF to publish")

        try:

            if not isinstance(eif_filename, str):
                self.logger.error(self.pretty_name + " error. eif_filename must be string")
                raise Exception("eif_filename not available")

            storage_context = StorageContext(self.settings)

            eif_origin = "".join((self.settings.storage_provider,
                                  "://",
                                  self.settings.publishing_buckets_prefix + self.settings.eif_bucket,
                                  "/", eif_filename))
        except Exception as e:

            self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                self.pretty_name, "error", e.message)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE


        success, error = self.set_eif_to_publish(storage_context, eif_origin)

        if success:
            self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                    self.pretty_name, "end", "Finished to set EIF to publish")
            return activity.activity.ACTIVITY_SUCCESS

        self.logger.error(error)
        self.emit_monitor_event(self.settings, data['article_id'], data['version'], data['run'],
                                self.pretty_name, "error", error)
        return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def set_eif_to_publish(self, storage_context, eif_origin):
        try:

            eif_data = self.get_eif(storage_context, eif_origin)

        except Exception as e:

            return False, "Could not fetch/load EIF data. Error details: " + e.message

        try:

            eif_data['publish'] = True
            storage_context.set_resource_from_string(eif_origin, json.dumps(eif_data))
            return True, None

        except Exception as e:
            return False, "There is something wrong with EIF data and/or we could not upload it. " \
                          "Error details: " + e.message

    def get_eif(self, storage_context, eif_origin):
        return json.loads(storage_context.get_resource_as_string(eif_origin))






