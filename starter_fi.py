import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
from optparse import OptionParser
import urlparse
import re

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
	#docs.append("elife00013.xml")
	#docs.append("elife_2013_00415.xml.zip")
	#docs.append("https://s3.amazonaws.com/elife-articles/00415/elife_2013_00415.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00013/elife00013.xml")
	"""
	docs.append("https://s3.amazonaws.com/elife-articles/00003/elife00003.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00005/elife00005.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00007/elife00007.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00011/elife00011.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00012/elife_2013_00012.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00013/elife00013.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00031/elife_2012_00031.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00047/elife_2012_00047.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00048/elife_2012_00048.xml.r6.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00049/elife00049.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00051/elife00051.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00065/elife00065.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00067/elife_2013_00067.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00068/elife00068.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00070/elife00070.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00078/elife00078.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00090/elife_2012_00090.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00093/elife_2012_00093.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00102/elife00102.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00105/elife_2013_00105.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00109/elife_2012_00109.xml.r2.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00116/elife_2013_00116.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00117/elife_2012_00117.xml.r2.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00133/elife_2013_00133.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00160/elife_2013_00160.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00170/elife_2013_00170.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00171/elife00171.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00173/elife00173.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00178/elife_2013_00178.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00181/elife_2012_00181.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00183/elife_2013_00183.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00184/elife_2012_00184.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00190/elife_2013_00190.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00205/elife_2012_00205.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00218/elife_2013_00218.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00230/elife_2013_00230.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00231/elife_2013_00231.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00240/elife_2012_00240.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00242/elife_2012_00242.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00243/elife_2012_00243.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00248/elife_2012_00248.xml.r2.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00260/elife_2013_00260.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00269/elife_2013_00269.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00270/elife00270.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00278/elife_2013_00278.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00281/elife_2012_00281.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00286/elife00286.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00288/elife_2013_00288.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00290/elife_2013_00290.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00291/elife_2013_00291.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00301/elife_2012_00301.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00302/elife_2012_00302.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00306/elife_2013_00306.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00308/elife_2013_00308.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00311/elife_2012_00311.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00312/elife_2013_00312.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00321/elife_2013_00321.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00326/elife00326.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00327/elife_2013_00327.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00329/elife_2013_00329.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00333/elife_2013_00333.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00336/elife_2013_00336.xml.r2.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00337/elife_2013_00337.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00340/elife00340.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00347/elife00347.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00348/elife_2013_00348.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00351/elife00351.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00352/elife_2012_00352.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00353/elife00353.xml")
	docs.append("https://s3.amazonaws.com/elife-articles/00354/elife_2013_00354.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00358/elife_2013_00358.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00362/elife_2013_00362.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00365/elife_2012_00365.xml.r2.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00367/elife_2013_00367.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00378/elife_2013_00378.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00385/elife_2012_00385.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00386/elife_2012_00386.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00387/elife_2012_00387.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00400/elife_2013_00400.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00415/elife_2013_00415.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00426/elife_2013_00426.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00435/elife_2013_00435.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00444/elife_2013_00444.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00450/elife_2013_00450.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00452/elife_2013_00452.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00458/elife_2013_00458.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00459/elife_2013_00459.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00461/elife_2013_00461.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00471/elife_2013_00471.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00473/elife_2013_00473.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00475/elife_2012_00475.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00476/elife_2013_00476.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00477/elife_2013_00477.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00481/elife_2013_00481.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00482/elife_2013_00482.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00488/elife_2013_00488.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00491/elife_2013_00491.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00499/elife_2013_00499.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00515/elife_2013_00515.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00534/elife_2013_00534.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00563/elife_2013_00563.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00565/elife_2013_00565.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00571/elife_2013_00571.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00572/elife_2013_00572.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00573/elife_2013_00573.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00577/elife_2013_00577.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00592/elife_2013_00592.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00593/elife_2013_00593.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00605/elife_2013_00605.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00615/elife_2013_00615.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00625/elife_2013_00625.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00638/elife_2013_00638.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00639/elife_2013_00639.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00641/elife_2013_00641.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00642/elife_2013_00642.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00646/elife_2013_00646.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00648/elife_2013_00648.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00655/elife_2013_00655.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00659/elife_2013_00659.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00663/elife_2013_00663.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00676/elife_2013_00676.xml.r1.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00692/elife_2013_00692.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00729/elife_2013_00729.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00767/elife_2013_00767.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00791/elife_2013_00791.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00799/elife_2013_00799.xml.zip")
	"""
	"""
	docs.append("https://s3.amazonaws.com/elife-articles/00473/elife_2013_00473.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00481/elife_2013_00481.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00592/elife_2013_00592.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00767/elife_2013_00767.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00791/elife_2013_00791.xml.zip")
	docs.append("https://s3.amazonaws.com/elife-articles/00799/elife_2013_00799.xml.zip")
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
		o = urlparse.urlparse(doc)
		
		start = False
		id_string = ""
		if(o.scheme == ""):
			document = '../elife-api-prototype/sample-xml/' + doc
			if(os.path.isfile(document)):
				start = True
				id_string = doc
		else:
			start = True
			id_string = re.sub(r'\W', '', o.path)
		
		# Start a workflow execution
		workflow_id = "PublishArticle_%s_%s" % (id_string, int(random.random() * 10000))
		#workflow_name = "PublishArticle"
		workflow_name = "PublishArticle"
		workflow_version = "1"
		child_policy = None
		execution_start_to_close_timeout = None
		input = '{"data": {"document": "' + doc + '"}}'

		# Temporary: Quick check for whether document exists before we start a workflow
		o = urlparse.urlparse(doc)
		start = False
		if(o.scheme == ""):
			document = '../elife-api-prototype/sample-xml/' + doc
			if(os.path.isfile(document)):
				start = True
		else:
			start = True
			
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