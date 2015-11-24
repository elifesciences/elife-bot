import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import settings as settingsLib
import log
import json
import random
from optparse import OptionParser

"""
Amazon SWF PublishArticle starter, for API and Lens publishing etc.
"""


class starter_PublishPerfectArticle():

    def start(self, ENV="dev", info=None):

        # TODO : much of this is common to many starters and could probably be streamlined

        # Specify run environment settings
        settings = settingsLib.get_settings(ENV)

        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        log_file = "starter.log"
        # logFile = None
        logger = log.logger(log_file, settings.setLevel, identity)

        filename = info.file_name

        if filename is None:
            logger.error("Did not get a filename")
            return

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        # Start a workflow execution
        workflow_id = "PublishPerfectArticle_%s" % filename.replace('/', '_') + str(int(random.random() * 1000))
        workflow_name = "PublishPerfectArticle"
        workflow_version = "1"
        child_policy = None
        execution_start_to_close_timeout = str(60 * 30)
        workflow_input = json.dumps(info, default=lambda ob: ob.__dict__)

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            logger.info(message)


if __name__ == "__main__":

    doi_id = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    parser.add_option("-f", "--filename", default=None, action="store", type="string", dest="filename",
                      help="specify the DOI id the article to process")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.filename:
        filename = options.filename

    o = starter_PublishPerfectArticle()

    o.start(ENV,)