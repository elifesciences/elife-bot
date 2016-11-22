import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import json
import random
from optparse import OptionParser

"""
Amazon SWF PostPerfectPublication starter, for API and Lens publishing etc.
"""

class NullRequiredDataException(Exception):
    pass


class starter_PostPerfectPublication():

    def start(self, info, settings, ENV="dev"):
        try:
            # Log
            identity = "starter_PostPerfectPublication.%s" % os.getpid()
            log_file = "starter.log"
            # logFile = None
            logger = log.logger(log_file, settings.setLevel, identity)

            if ('article_id', 'version', 'run') not in info or \
                            info['article_id'] is None or \
                            info['version'] is None or \
                            info['run'] is None:
                raise NullRequiredDataException("article id, version or run is Null. Possible error: "
                                                "Lax did not send back valid data from ingest.")

            workflow_id, \
            workflow_name, \
            workflow_version, \
            child_policy, \
            execution_start_to_close_timeout, \
            workflow_input = self.set_workflow_information("PostPerfectPublication", "1", None, info)

            # Simple connect
            conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except NullRequiredDataException:
            logger.exception()

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: ' \
                      'There is already a running workflow with ID %s' % workflow_id
            logger.info(message)

    def set_workflow_information(self, name, workflow_version, child_policy, data):
        publication_from = "lax" if 'requested_action' in data else 'website'
        workflow_id = "%s_%s.%s" % (name, data['article_id'], publication_from)
        workflow_name = "PostPerfectPublication"
        workflow_version = workflow_version
        child_policy = child_policy
        execution_start_to_close_timeout = str(60 * 30)
        workflow_input = json.dumps(data, default=lambda ob: ob.__dict__)

        return  workflow_id, \
                workflow_name, \
                workflow_version, \
                child_policy, \
                execution_start_to_close_timeout, \
                workflow_input


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

    o = starter_PostPerfectPublication()

    o.start(ENV,)