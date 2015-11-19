import os
# Add parent directory for imports
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
from optparse import OptionParser

import provider.simpleDB as dblib

"""
Amazon SWF PublishLensJPG starter
"""

class starter_PublishLensJPG():

    def start(self, ENV = "dev", doi_id = None,  document = None, last_updated_since = None):
        # Specify run environment settings
        settings = settingsLib.get_settings(ENV)
        
        # Log
        identity = "starter_%s" % int(random.random() * 1000)
        logFile = "starter.log"
        #logFile = None
        logger = log.logger(logFile, settings.setLevel, identity)
        
        # Simple connect
        conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)
    
        if document is not None and doi_id is not None:
            
            docs = []
            doc = {}
            doc['document'] = document
            doc['elife_id'] = doi_id
            docs.append(doc)
        elif(last_updated_since is not None):
            # Publish only articles since the last_modified date, use SimpleDB as the source
            docs = self.get_docs_from_SimpleDB(ENV, last_updated_since = last_updated_since)
        
        if(docs):
            for doc in docs:
                
                document = doc["document"]
                elife_id = doc["elife_id"]
        
                id_string = elife_id
        
                # Start a workflow execution
                workflow_id = "PublishLensJPG_%s" % (id_string)
                workflow_name = "PublishLensJPG"
                workflow_version = "1"
                child_policy = None
                execution_start_to_close_timeout = str(60*30)
                input = '{"data": ' + json.dumps(doc) + '}'
        
                try:
                    response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)
        
                    logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))
                    
                except boto.swf.exceptions.SWFWorkflowExecutionAlreadyStartedError:
                    # There is already a running workflow with that ID, cannot start another
                    message = 'SWFWorkflowExecutionAlreadyStartedError: There is already a running workflow with ID %s' % workflow_id
                    print message
                    logger.info(message)

    def get_docs_from_SimpleDB(self, ENV = "dev", last_updated_since = None):
        """
        Get the array of docs from the SimpleDB provider
        """
        docs = []
    
        # Specify run environment settings
        settings = settingsLib.get_settings(ENV)
        
        db = dblib.SimpleDB(settings)
        db.connect()
        
        if(last_updated_since is not None):
            file_list = db.elife_get_lens_jpg_S3_file_items(last_updated_since = last_updated_since)
        else:
            # Get all - not implemented for now to avoid mistakes running too many workflows
            pass
            
        for x in file_list:
            tmp = {}
            name = x['name']
            tmp['document'] = name
            
            # Extract the DOI from the file name, example file name
            #   elife-00353-vor-v1.zip
            doi_id = None
            try:
                part = name.split('elife-')[1]
                doi_id = part.split('.')[0]
            except:
                doi_id = None
                
            if doi_id:
                tmp['elife_id'] = doi_id
                docs.append(tmp)
        
        return docs

if __name__ == "__main__":

    doi_id = None
    document = None
    last_updated_since = None
    all = False
    
    # Add options
    parser = OptionParser()
    parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
    parser.add_option("-d", "--doi-id", default=None, action="store", type="string", dest="doi_id", help="specify the DOI id of a single article")
    parser.add_option("-f", "--file", default=None, action="store", type="string", dest="document", help="specify the S3 object name of the zip file")
    parser.add_option("-u", "--last-updated-since", default=None, action="store", type="string", dest="last_updated_since", help="specify the datetime for last_updated_since")
    
    (options, args) = parser.parse_args()
    if options.env: 
        ENV = options.env
    if options.doi_id:
        doi_id = options.doi_id
    if options.document:
        document = options.document
    if options.last_updated_since:
        last_updated_since = options.last_updated_since

    o = starter_PublishLensJPG()

    o.start(ENV, doi_id = doi_id, document = document, last_updated_since = last_updated_since)