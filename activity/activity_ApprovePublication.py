import json
import activity
import os
import requests


"""
ConvertJATS.py activity
"""
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

class activity_ApprovePublication(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "ApprovePublication"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Approve a previously submitted article"
        self.rules = []
        self.info = None
        self.logger = logger
        # TODO : better exception handling


    def do_activity(self, data=None):
        """
        Do the work
        """
        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        article_version_id = data

        destination = self.settings.drupal_approve_endpoint
        destination = destination + article_version_id + '.json'

        headers = {'content-type': 'application/json'}
        r = requests.put(destination, data="{ \"publish\": \"1\" }", headers=headers)
        self.logger.info("PUT response was %s" % r.status_code)
        return True

