import os
import boto.swf.exceptions

# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import log
import json
import random
from optparse import OptionParser

import starter.starter_helper as helper
from starter.starter_helper import NullRequiredDataException

"""
Amazon SWF PublishArticle starter, for API and Lens publishing etc.
"""


class starter_ApproveArticlePublication():
    def __init__(self):
        self.const_name = "ApproveArticlePublication"

    def start(self, settings, article_id=None, version=None, run=None, publication_data=None):

        # TODO : much of this is common to many starters and could probably be streamlined

        # Log
        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if article_id is None or version is None or publication_data is None:
            raise NullRequiredDataException("Did not get an article id, version or publication data")

        info = {
            'article_id': article_id,
            'version': str(version),
            'run': run,
            'publication_data': publication_data
        }

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(self.const_name, "1", None, info,
                                                         article_id + "." + str(version))

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
            message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
            logger.info(message)


def main():

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env",
                      help="set the environment to run, either dev or live")
    parser.add_option("-i", "--article-version-id", default=None, action="store", type="string",
                      dest="article_version_id",
                      help="specify the DOI id the article to process")

    (options, args) = parser.parse_args()
    ENV = None
    if options.env:
        ENV = options.env
    article_version_id = None
    if options.article_version_id:
        article_version_id = options.article_version_id

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_ApproveArticlePublication()

    o.start(settings=settings, article_version_id=article_version_id)

if __name__ == "__main__":
    main()
