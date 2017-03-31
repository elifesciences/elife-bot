import os
import boto.swf.exceptions

# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, parentdir)

import boto.swf
import json
from argparse import ArgumentParser

import starter_helper as helper
from starter_helper import NullRequiredDataException

"""
Amazon SWF CopyGlencoeStillImages starter, for copying Glencoe still images to IIIF bucket.
"""


class starter_CopyGlencoeStillImages():
    def __init__(self):
        self.const_name = "CopyGlencoeStillImages"

    def start(self, settings, article_id=None, version=None, run=None, standalone=False, standalone_is_poa=False):

        # Log
        logger = helper.get_starter_logger(settings.setLevel, helper.get_starter_identity(self.const_name))

        if article_id is None:
            raise NullRequiredDataException("Did not get an article id. Required.")

        info = {
            'run': run,
            'article_id': article_id,
            'version': version,
            'standalone': standalone,
            'standalone_is_poa': standalone_is_poa
        }

        workflow_id, \
        workflow_name, \
        workflow_version, \
        child_policy, \
        execution_start_to_close_timeout, \
        workflow_input = helper.set_workflow_information(self.const_name, "1", None, info, article_id)

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

    # example on how to run:
    # From elife-bot folder run
    # python starter/starter_CopyGlencoeStillImages.py --env=dev --article-id=15224 --no-poa

    parser = ArgumentParser()
    parser.add_argument("-e", "--env", action="store", type=str, dest="env",
                        help="set the environment to run, e.g. dev, live, prod, end2end")
    parser.add_argument("-a", "--article-id", action="store", type=str, dest="article_id",
                        help="specify the article id to process")
    parser.add_argument("-p", "--poa", action="store_true", dest="poa",
                        help="Article is POA. If omitted it defaults to False.")
    parser.add_argument("-np", "--no-poa", action="store_false", dest="poa",
                        help="Article is NOT POA. If omitted it defaults to False.")
    parser.set_defaults(env="dev", article_id=None, poa=False)

    args = parser.parse_args()
    ENV = None
    if args.env:
        ENV = args.env
    article_id = None
    is_poa = False
    if args.article_id:
        article_id = args.article_id
    if args.poa:
        is_poa = args.poa

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_CopyGlencoeStillImages()

    o.start(settings=settings, article_id=article_id, standalone=True, standalone_is_poa=is_poa)

if __name__ == "__main__":
    main()
