import os
# Add parent directory for imports, so activity classes can use elife-api-prototype
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
Amazon SWF LensArticlePublish starter
"""

def start(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)
	
	# Log
	identity = "starter_%s" % int(random.random() * 1000)
	logFile = "starter.log"
	#logFile = None
	logger = log.logger(logFile, settings.setLevel, identity)
	
	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	docs = []
	#docs.append({"elife_id":"00013","document":"https://s3.amazonaws.com/elife-articles/00013/elife00013.xml"})
	#docs.append({"elife_id":"00415","document":"https://s3.amazonaws.com/elife-articles/00415/elife_2013_00415.xml.zip"})
	"""
	docs.append({"elife_id":"00415","document":"https://s3.amazonaws.com/elife-articles/00415/elife_2013_00415.xml.zip"})
	docs.append({"elife_id":"00873","document":"https://s3.amazonaws.com/elife-articles/00873/elife_2013_00873.xml.r1.zip"})
	docs.append({"elife_id":"00334","document":"https://s3.amazonaws.com/elife-articles/00334/elife_2013_00334.xml.zip"})
	docs.append({"elife_id":"00425","document":"https://s3.amazonaws.com/elife-articles/00425/elife_2013_00425.xml.zip"})
	docs.append({"elife_id":"00498","document":"https://s3.amazonaws.com/elife-articles/00498/elife_2013_00498.xml.zip"})
	docs.append({"elife_id":"00658","document":"https://s3.amazonaws.com/elife-articles/00658/elife_2013_00658.xml.zip"})
	docs.append({"elife_id":"00731","document":"https://s3.amazonaws.com/elife-articles/00731/elife_2013_00731.xml.zip"})
	docs.append({"elife_id":"00856","document":"https://s3.amazonaws.com/elife-articles/00856/elife_2013_00856.xml.zip"})
	docs.append({"elife_id":"00866","document":"https://s3.amazonaws.com/elife-articles/00866/elife_2013_00866.xml.zip"})
	docs.append({"elife_id":"00895","document":"https://s3.amazonaws.com/elife-articles/00895/elife_2013_00895.xml.zip"})
	"""
	"""
	docs.append({"elife_id":"00117","document":"https://s3.amazonaws.com/elife-articles/00117/elife_2012_00117.xml.r2.zip"})
	docs.append({"elife_id":"00171","document":"https://s3.amazonaws.com/elife-articles/00171/elife00171.xml"})
	docs.append({"elife_id":"00278","document":"https://s3.amazonaws.com/elife-articles/00278/elife_2013_00278.xml.zip"})
	docs.append({"elife_id":"00290","document":"https://s3.amazonaws.com/elife-articles/00290/elife_2013_00290.xml.zip"})
	docs.append({"elife_id":"00333","document":"https://s3.amazonaws.com/elife-articles/00333/elife_2013_00333.xml.zip"})
	docs.append({"elife_id":"00362","document":"https://s3.amazonaws.com/elife-articles/00362/elife_2013_00362.xml.zip"})
	docs.append({"elife_id":"00378","document":"https://s3.amazonaws.com/elife-articles/00378/elife_2013_00378.xml.zip"})
	docs.append({"elife_id":"00444","document":"https://s3.amazonaws.com/elife-articles/00444/elife_2013_00444.xml.zip"})
	docs.append({"elife_id":"00461","document":"https://s3.amazonaws.com/elife-articles/00461/elife_2013_00461.xml.zip"})
	docs.append({"elife_id":"00757","document":"https://s3.amazonaws.com/elife-articles/00757/elife_2013_00757.xml.zip"})
	"""

	db = dblib.SimpleDB(settings)
	db.connect()
	xml_item_list = db.elife_get_article_S3_file_items(file_data_type = "xml", latest = True)
	for x in xml_item_list:
		tmp = {}
		elife_id = str(x['name']).split("/")[0]
		document = 'https://s3.amazonaws.com/' + x['item_name']
		tmp['elife_id'] = elife_id
		tmp['document'] = document
		docs.append(tmp)

	#docs.append({"elife_id":"00537","document":"https://s3.amazonaws.com/elife-articles/00537/elife_2013_00537.xml.zip"})
	
	for doc in docs:
		
		document = doc["document"]
		elife_id = doc["elife_id"]

		id_string = elife_id
		start = True

		# Start a workflow execution
		workflow_id = "LensArticlePublish_%s" % (id_string)
		workflow_name = "LensArticlePublish"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = str(60*60*2)
		input = '{"data": ' + json.dumps(doc) + '}'

		if(start):
			response = conn.start_workflow_execution(settings.domain, workflow_id, workflow_name, workflow_version, settings.default_task_list, child_policy, execution_start_to_close_timeout, input)

			logger.info('got response: \n%s' % json.dumps(response, sort_keys=True, indent=4))

if __name__ == "__main__":

	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env: 
		ENV = options.env

	start(ENV)