import boto.swf
import log
import json
import random
from optparse import OptionParser

"""
Amazon SWF LensArticlePublish starter
"""


class starter_LensArticlePublish():

    def start(self, settings, all_doi=None, doi_id=None):
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        docs = []

        if all_doi is True:
            # Publish all articles
            # TODO!! Add all articles support again
            pass

        elif doi_id is not None:
            doc = {}
            doc['article_id'] = str(doi_id).zfill(5)
            docs.append(doc)

        if docs:
            for doc in docs:

                article_id = doc["article_id"]

                # Start a workflow execution
                workflow_id = "LensArticlePublish_%s" % (article_id)
                workflow_name = "LensArticlePublish"
                workflow_version = "1"
                child_policy = None
                execution_start_to_close_timeout = str(60 * 30)
                input = '{"article_id": "' + str(article_id) + '"}'

                try:
                    response = conn.start_workflow_execution(
                        settings.domain, workflow_id, workflow_name, workflow_version,
                        settings.default_task_list, child_policy, execution_start_to_close_timeout,
                        input)

                    logger.info('got response: \n%s' %
                                json.dumps(response, sort_keys=True, indent=4))

                except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                    # There is already a running workflow with that ID, cannot start another
                    message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                               'a running workflow with ID %s' % workflow_id)
                    print(message)
                    logger.info(message)

if __name__ == "__main__":

    doi_id = None
    all_doi = False

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string",
                      dest="env", help="set the environment to run, either dev or live")
    parser.add_option("-d", "--doi-id", default=None, action="store", type="string",
                      dest="doi_id", help="specify the DOI id of a single article")
    parser.add_option("-a", "--all", default=None, action="store_true", dest="all_doi",
                      help="start workflow for all article DOI")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.doi_id:
        doi_id = options.doi_id
    if options.all_doi:
        all_doi = options.all_doi

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_LensArticlePublish()

    o.start(settings=settings, all_doi=all_doi, doi_id=doi_id)
