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
	
	# Fluidinfo settings
	fi_namespace = "elifesciences.org/api_dev"
	
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
	
	# Fluidinfo settings
	fi_namespace = "elifesciences.org/api_v1"
	
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
	
	# Logging
	setLevel = "INFO"
	
def get_settings(ENV = "dev"):
	"""
	Return the settings class based on the environment type provided,
	by default use the dev environment settings
	"""
	return eval(ENV)


