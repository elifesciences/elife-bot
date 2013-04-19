import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
from optparse import OptionParser

"""
Amazon SWF workflow starter
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
	"""
	docs.append("elife00003.xml")
	docs.append("elife00005.xml")
	docs.append("elife00007.xml")
	docs.append("elife00011.xml")
	docs.append("elife00012.xml")
	"""
	docs.append("elife00013.xml")
	"""
	docs.append("elife00031.xml")
	docs.append("elife00047.xml")
	docs.append("elife00048.xml")
	docs.append("elife00049.xml")
	docs.append("elife00051.xml")
	docs.append("elife00065.xml")
	docs.append("elife00067.xml")
	docs.append("elife00068.xml")
	docs.append("elife00070.xml")
	docs.append("elife00078.xml")
	docs.append("elife00090.xml")
	docs.append("elife00093.xml")
	docs.append("elife00102.xml")
	docs.append("elife00105.xml")
	docs.append("elife00109.xml")
	docs.append("elife00116.xml")
	docs.append("elife00117.xml")
	docs.append("elife00160.xml")
	docs.append("elife00170.xml")
	docs.append("elife00171.xml")
	docs.append("elife00173.xml")
	docs.append("elife00178.xml")
	docs.append("elife00181.xml")
	docs.append("elife00183.xml")
	docs.append("elife00184.xml")
	docs.append("elife00205.xml")
	docs.append("elife00230.xml")
	docs.append("elife00231.xml")
	docs.append("elife00240.xml")
	docs.append("elife00242.xml")
	docs.append("elife00243.xml")
	docs.append("elife00248.xml")
	docs.append("elife00270.xml")
	docs.append("elife00281.xml")
	docs.append("elife00286.xml")
	docs.append("elife00290.xml")
	docs.append("elife00291.xml")
	docs.append("elife00301.xml")
	docs.append("elife00302.xml")
	docs.append("elife00306.xml")
	docs.append("elife00308.xml")
	docs.append("elife00311.xml")
	docs.append("elife00321.xml")
	docs.append("elife00326.xml")
	docs.append("elife00329.xml")
	docs.append("elife00333.xml")
	docs.append("elife00340.xml")
	docs.append("elife00347.xml")
	docs.append("elife00348.xml")
	docs.append("elife00351.xml")
	docs.append("elife00352.xml")
	docs.append("elife00353.xml")
	docs.append("elife00365.xml")
	docs.append("elife00385.xml")
	docs.append("elife00386.xml")
	docs.append("elife00387.xml")
	docs.append("elife00400.xml")
	docs.append("elife00450.xml")
	docs.append("elife00452.xml")
	docs.append("elife00461.xml")
	docs.append("elife00471.xml")
	docs.append("elife00475.xml")
	docs.append("elife00476.xml")
	docs.append("elife00477.xml")
	docs.append("elife00488.xml")
	docs.append("elife00491.xml")
	docs.append("elife00515.xml")
	docs.append("elife00563.xml")
	docs.append("elife00565.xml")
	docs.append("elife00571.xml")
	docs.append("elife00572.xml")
	docs.append("elife00573.xml")
	docs.append("elife00593.xml")
	docs.append("elife00327.xml")
	docs.append("elife00218.xml")
	docs.append("elife00190.xml")
	docs.append("elife00337.xml")
	docs.append("elife00133.xml")
	docs.append("elife00615.xml")
	docs.append("elife00577.xml")
	docs.append("elife00646.xml")
	docs.append("elife00638.xml")
	docs.append("elife00641.xml")
	docs.append("elife00378.xml")
	docs.append("elife00354.xml")
	docs.append("elife00336.xml")
	docs.append("elife00312.xml")
	docs.append("elife00605.xml")
	docs.append("elife00260.xml")
	docs.append("elife00269.xml")
	docs.append("elife00625.xml")
	docs.append("elife00642.xml")
	docs.append("elife00648.xml")
	docs.append("elife00278.xml")
	docs.append("elife00367.xml")
	docs.append("elife00435.xml")
	docs.append("elife00482.xml")
	docs.append("elife00639.xml")
	docs.append("elife00655.xml")
	docs.append("elife00426.xml")
	docs.append("elife00444.xml")
	docs.append("elife00499.xml")
	docs.append("elife00659.xml")
	docs.append("elife00663.xml")
	docs.append("elife00692.xml")
	docs.append("elife00362.xml")
	docs.append("elife00288.xml")
	docs.append("elife00459.xml")
	docs.append("elife00458.xml")
	docs.append("elife00534.xml")
	docs.append("elife00676.xml")
	docs.append("elife00415.xml")
	docs.append("elife00729.xml")
	"""

	for doc in docs:
		# Start a workflow execution
		workflow_id = "PublishArticle_%s_%s" % (doc, int(random.random() * 10000))
		#workflow_name = "PublishArticle"
		workflow_name = "PublishArticle"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = None
		input = '{"data": {"document": "' + doc + '"}}'

		# Temporary: Quick check for whether document exists before we start a workflow
		document = '../elife-api-prototype/sample-xml/' + doc

		if(os.path.isfile(document)):
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