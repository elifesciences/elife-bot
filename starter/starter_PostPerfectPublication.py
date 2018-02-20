import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import json
from optparse import OptionParser
import starter_helper as helper
from starter_helper import NullRequiredDataException

"""
Amazon SWF PostPerfectPublication starter, for API and Lens publishing etc.
"""

class starter_PostPerfectPublication():
    def __init__(self):
        self.const_name = "PostPerfectPublication"


    def start(self, info, settings):

        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if info['article_id'] is None:
            raise NullRequiredDataException("article id is Null. Possible error: "
                                            "Lax did not send back valid data from ingest.")

        publication_from = "lax" if 'requested_action' in info else 'website'

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(
            self.const_name, "1", None, info, "%s.%s" % (info.get('article_id'), info.get('version')),
            publication_from)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        try:
            response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version,
                                                     settings.default_task_list, child_policy,
                                                     execution_start_to_close_timeout, workflow_input)

            logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

        except NullRequiredDataException as e:
            logger.exception(e.message)
            raise

        except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
            # There is already a running workflow with that ID, cannot start another
            message = 'SWFWorkflowExecutionAlreadyStartedError: ' \
                      'There is already a running workflow with ID %s' % workflow_id
            logger.error(message)


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

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_PostPerfectPublication()

    o.start(settings=settings,info={})
