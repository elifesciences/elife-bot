import activity
import json
import boto.swf

"""
ConvertJATS.py activity
"""


class activity_ConvertJATS(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ConvertJATS"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Process a JATS xml file into .... something else"

    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        # TODO : add the rest!
        #elife_id = data["data"]["elife_id"]
        #document = data["data"]["document"]
        #self.fs.write_document_to_tmp_dir(document)
        self.result = True 
        return True

