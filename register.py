import boto.swf
import settings as settingsLib
import log
import json
import random
import datetime
import os
from optparse import OptionParser
import importlib
import workflow
import activity

# Add parent directory for imports, so activity classes can use elife-api-prototype
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir)

"""
Amazon SWF register workflow or activity utility
"""

def start(ENV = "dev"):
	# Specify run environment settings
	settings = settingsLib.get_settings(ENV)

	# Simple connect
	conn = boto.swf.layer1.Layer1(settings.aws_access_key_id, settings.aws_secret_access_key)

	workflow_names = []
	workflow_names.append("Ping")
	workflow_names.append("Sum")
	workflow_names.append("ApproveArticlePublication")
	workflow_names.append("PublishArticle")
	workflow_names.append("NewS3File")
	workflow_names.append("S3Monitor")
	workflow_names.append("LensArticlePublish")
	workflow_names.append("LensIndexPublish")
	workflow_names.append("AdminEmail")
	workflow_names.append("PublishPDF")
	workflow_names.append("PublishSVG")
	workflow_names.append("SendQueuedEmail")
	workflow_names.append("PublishSuppl")
	workflow_names.append("PublishJPG")
	workflow_names.append("PackagePOA")
	workflow_names.append("PublishPOA")
	workflow_names.append("DepositCrossref")
	workflow_names.append("PubmedArticleDeposit")
	workflow_names.append("PublishFiguresPDF")
	workflow_names.append("PublicationEmail")
	workflow_names.append("FTPArticle")
	workflow_names.append("PubRouterDeposit")
	workflow_names.append("PublishPerfectArticle")
	workflow_names.append("ProcessXMLArticle")

	for workflow_name in workflow_names:
		# Import the workflow libraries
		class_name = "workflow_" + workflow_name
		module_name = "workflow." + class_name
		importlib.import_module(module_name)
		full_path = "workflow." + class_name + "." + class_name
		# Create the workflow object
		f = eval(full_path)
		logger = None
		workflow_object = f(settings, logger, conn)

		# Now register it
		response = workflow_object.register()

		print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)

	activity_names = []
	activity_names.append("PingWorker")
	activity_names.append("SetPublicationStatus")
	activity_names.append("ConvertJATS")
	activity_names.append("ExpandArticle")
	activity_names.append("ApplyVersionNumber")
	activity_names.append("ApprovePublication")
	activity_names.append("ResizeImages")
	activity_names.append("PostEIF")
	activity_names.append("ProcessNewS3File")
	activity_names.append("Sum")
	activity_names.append("S3Monitor")
	activity_names.append("UnzipArticleXML")
	activity_names.append("ConverterXMLtoJS")
	activity_names.append("LensDocumentsJS")
	activity_names.append("LensXMLFilesList")
	activity_names.append("LensCDNInvalidation")
	activity_names.append("AdminEmailHistory")
	activity_names.append("WorkflowConflictCheck")
	activity_names.append("UnzipArticlePDF")
	activity_names.append("UnzipArticleSVG")
	activity_names.append("SendQueuedEmail")
	activity_names.append("LensArticle")
	activity_names.append("UnzipArticleSuppl")
	activity_names.append("UnzipArticleJPG")
	activity_names.append("ConverterSVGtoJPG")
	activity_names.append("PackagePOA")
	activity_names.append("PublishPOA")
	activity_names.append("DepositCrossref")
	activity_names.append("PubmedArticleDeposit")
	activity_names.append("ArticleToOutbox")
	activity_names.append("UnzipArticleFiguresPDF")
	activity_names.append("PublicationEmail")
	activity_names.append("FTPArticle")
	activity_names.append("PubRouterDeposit")

	for activity_name in activity_names:
		# Import the activity libraries
		class_name = "activity_" + activity_name
		module_name = "activity." + class_name
		importlib.import_module(module_name)
		full_path = "activity." + class_name + "." + class_name
		# Create the workflow object
		f = eval(full_path)
		logger = None
		activity_object = f(settings, logger, conn)

		# Now register it
		response = activity_object.register()

		print 'got response: \n%s' % json.dumps(response, sort_keys=True, indent=4)

if __name__ == "__main__":

	# Add options
	parser = OptionParser()
	parser.add_option("-e", "--env", default="dev", action="store", type="string", dest="env", help="set the environment to run, either dev or live")
	(options, args) = parser.parse_args()
	if options.env:
		ENV = options.env

	start(ENV)