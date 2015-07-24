"""
	Settings for eLife
	~~~~~~~~~~~
	To specify multiple environments, each environment gets its own class,
	and calling get_settings will return the specified class that contains
	the settings.
	
	You must modify:
		aws_access_key_id
		aws_secret_access_key

"""

class dev():
	# AWS settings
	aws_access_key_id = '<your access key>'
	aws_secret_access_key = '<your secret key>'
	
	# S3 settings
	bucket = 'elife-articles'
	prefix = ''
	delimiter = '/'
	
	# SWF queue settings
	domain = "Publish.dev"
	default_task_list = "DefaultTaskList"
	
	# SimpleDB settings
	simpledb_region = "us-east-1"
	simpledb_domain_postfix = "_dev"
	
	# Converter settings
	converter_url = ""
	converter_token = "abcd"
	
	# SES settings
	# email needs to be verified by AWS
	ses_region = "us-east-1"
	ses_sender_email = "sender@example.com"
	ses_admin_email = "admin@example.com"
	
	# CDN bucket settings
	cdn_bucket = 'elife-cdn-dev'
	cdn_distribution_id = u'E1HPZ2QWOYE9NX'
	cdn_domain_name = 'dhkzd83nokruv.cloudfront.net'
	
	# Lens bucket settings
	lens_bucket = 'elife-lens-dev'
	lens_distribution_id = u'E30WWCB2DNEOKI'
	lens_domain_name = 'd32g8kubfuccxs.cloudfront.net'
	
	# Bot S3 settings
	bot_bucket = 'elife-bot-dev'
	
	# POA delivery bucket
	poa_bucket = 'elife-ejp-poa-delivery-dev'
	
	# POA packaging bucket
	poa_packaging_bucket = 'elife-poa-packaging-dev'
	
	# POA FTP settings
	POA_FTP_URI = ""
	POA_FTP_USERNAME = ""
	POA_FTP_PASSWORD = ""
	POA_FTP_CWD = ""
	
	# POA email settings
	ses_poa_sender_email = "sender@example.com"
	ses_poa_recipient_email = "admin@example.com"
	
	# EJP S3 settings
	ejp_bucket = 'elife-ejp-ftp-dev'
	
	# Templates S3 settings
	templates_bucket = 'elife-bot-dev'
	
	# Crossref
	crossref_url = 'http://test.crossref.org/servlet/deposit'
	crossref_login_id = ''
	crossref_login_passwd = ''
	
	# PubMed FTP settings
	PUBMED_FTP_URI = ""
	PUBMED_FTP_USERNAME = ""
	PUBMED_FTP_PASSWORD = ""
	PUBMED_FTP_CWD = ""
		
	# HEFCE Archive FTP settings
	HEFCE_FTP_URI = ""
	HEFCE_FTP_USERNAME = ""
	HEFCE_FTP_PASSWORD = ""
	HEFCE_FTP_CWD = ""
	
	# Cengage Archive FTP settings
	CENGAGE_FTP_URI = ""
	CENGAGE_FTP_USERNAME = ""
	CENGAGE_FTP_PASSWORD = ""
	CENGAGE_FTP_CWD = ""
	
	# GoOA FTP settings
	GOOA_FTP_URI = ""
	GOOA_FTP_USERNAME = ""
	GOOA_FTP_PASSWORD = ""
	GOOA_FTP_CWD = ""
	
	# Logging
	setLevel = "INFO"
	
class live():
	# AWS settings
	aws_access_key_id = '<your access key>'
	aws_secret_access_key = '<your secret key>'
	
	# S3 settings
	bucket = 'elife-articles'
	prefix = ''
	delimiter = '/'
	
	# SWF queue settings
	domain = "Publish"
	default_task_list = "DefaultTaskList"
	
	# Converter settings
	converter_url = ""
	converter_token = "abcd"
	
	# SimpleDB settings
	simpledb_region = "us-east-1"
	simpledb_domain_postfix = ""
	
	# SES settings
	# email needs to be verified by AWS
	ses_region = "us-east-1"
	ses_sender_email = "sender@example.com"
	ses_admin_email = "admin@example.com"
	
	# CDN bucket settings
	cdn_bucket = 'elife-cdn'
	cdn_distribution_id = u'E3EXVOTTI6XCOZ'
	cdn_domain_name = 'cdn.elifesciences.org'
	
	# Lens bucket settings
	lens_bucket = 'elife-lens'
	lens_distribution_id = u'EK4HKRQWIF6B3'
	cdn_domain_name = 'lens.elifesciences.org'
	
	# Bot S3 settings
	bot_bucket = 'elife-bot'
	
	# POA delivery bucket
	poa_bucket = 'elife-ejp-poa-delivery'
	
	# POA packaging bucket
	poa_packaging_bucket = 'elife-poa-packaging'
	
	# POA FTP settings
	POA_FTP_URI = ""
	POA_FTP_USERNAME = ""
	POA_FTP_PASSWORD = ""
	POA_FTP_CWD = ""
	
	# POA email settings
	ses_poa_sender_email = "sender@example.com"
	ses_poa_recipient_email = "admin@example.com"
	
	# EJP S3 settings
	ejp_bucket = 'elife-ejp-ftp'
	
	# Templates S3 settings
	templates_bucket = 'elife-bot'
	
	# Crossref
	crossref_url = 'http://doi.crossref.org/servlet/deposit'
	crossref_login_id = ''
	crossref_login_passwd = ''
	
	# PubMed FTP settings
	PUBMED_FTP_URI = ""
	PUBMED_FTP_USERNAME = ""
	PUBMED_FTP_PASSWORD = ""
	PUBMED_FTP_CWD = ""
		
	# HEFCE Archive FTP settings
	HEFCE_FTP_URI = ""
	HEFCE_FTP_USERNAME = ""
	HEFCE_FTP_PASSWORD = ""
	HEFCE_FTP_CWD = ""
	
	# Cengage Archive FTP settings
	CENGAGE_FTP_URI = ""
	CENGAGE_FTP_USERNAME = ""
	CENGAGE_FTP_PASSWORD = ""
	CENGAGE_FTP_CWD = ""
	
	# GoOA FTP settings
	GOOA_FTP_URI = ""
	GOOA_FTP_USERNAME = ""
	GOOA_FTP_PASSWORD = ""
	GOOA_FTP_CWD = ""
	
	# Logging
	setLevel = "INFO"
	
def get_settings(ENV = "dev"):
	"""
	Return the settings class based on the environment type provided,
	by default use the dev environment settings
	"""
	return eval(ENV)


