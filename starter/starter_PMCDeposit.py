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
Amazon SWF PMCDeposit starter
"""

class starter_PMCDeposit():

    def start(self, settings, bucket=None, document=None):
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)

        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

        docs = None

        if document is not None:
            docs = []
            doc = {}
            doc["document"] = document
            if bucket is not None:
                doc["bucket"] = bucket
            docs.append(doc)

        if docs:
            for doc in docs:

                document = doc["document"]

                # Get a unique id from the document name for the workflow_id
                id_string = None
                try:
                    id_string = ''
                    document_file = document.split("/")[-1]
                    if "bucket" in doc:
                        id_string += doc['bucket'] + '_'
                    id_string += document_file.split("_")[0]
                except:
                    id_string = "000"

                # Start a workflow execution
                workflow_id = "PMCDeposit_%s" % (id_string)
                workflow_name = "PMCDeposit"
                workflow_version = "1"
                child_policy = None
                execution_start_to_close_timeout = None
                input = '{"data": ' + json.dumps(doc) + '}'

                try:
                    response = conn.start_workflow_execution(settings.domain, workflow_id,
                                                             workflow_name, workflow_version,
                                                             settings.default_task_list,
                                                             child_policy,
                                                             execution_start_to_close_timeout,
                                                             input)

                    logger.info('got response: \n%s' %
                                json.dumps(response, sort_keys=True, indent=4))

                except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                    # There is already a running workflow with that ID, cannot start another
                    message = ('SWFWorkflowExecutionAlreadyStartedError: There is already ' +
                               'a running workflow with ID %s' % workflow_id)
                    print message
                    logger.info(message)


if __name__ == "__main__":

    document = None
    bucket = None
    last_updated_since = None

    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string",
                      dest="env", help="set the environment to run, either dev or live")
    parser.add_option("-b", "--bucket", default=None, action="store", type="string",
                      dest="bucket", help="specify the bucket where the file is")
    parser.add_option("-f", "--file", default=None, action="store", type="string",
                      dest="document", help="specify the S3 object name of the POA zip file")

    (options, args) = parser.parse_args()
    if options.env:
        ENV = options.env
    if options.document:
        document = options.document
    if options.bucket:
        bucket = options.bucket

    import settings as settingsLib
    settings = settingsLib.get_settings(ENV)

    o = starter_PMCDeposit()

    o.start(settings=settings, bucket=bucket, document=document)
