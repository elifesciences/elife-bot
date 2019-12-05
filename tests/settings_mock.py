
domain = ""
default_task_list = ""

storage_provider = 's3'
expanded_bucket = 'origin_bucket'

publishing_buckets_prefix = ""
production_bucket = "production_bucket"

bucket = ""

s3_session_bucket = "origin_bucket"

aws_access_key_id = ""
aws_secret_access_key = ""

workflow_starter_queue = ""
sqs_region = ""


simpledb_region = ""
simpledb_domain_postfix = "_test"
ejp_bucket = 'ejp_bucket'
templates_bucket = 'templates_bucket'
ppp_cdn_bucket = 'ppd_cdn_bucket'
archive_bucket = "archive_bucket"
bot_bucket = 'bot_bucket'
lens_bucket = 'dest_bucket'
poa_packaging_bucket = 'poa_packaging_bucket'
poa_bucket = 'poa_bucket'
ses_poa_sender_email = ""
ses_poa_recipient_email = ""

lax_article_versions = 'https://test/eLife.{article_id}/version/'
verify_ssl = False
lax_auth_key = 'an_auth_key'

digest_config_file = 'tests/activity/digest.cfg'
digest_config_section = 'elife'

digest_endpoint = 'https://digests/{digest_id}'
digest_auth_key = 'digest_auth_key'

no_download_extensions = 'tif'

crossref_url = ""
crossref_login_id = ""
crossref_login_passwd = ""

# Logging
setLevel = "INFO"

# PDF cover
pdf_cover_generator = "https://localhost/personalised-covers/"
pdf_cover_landing_page = "https://localhost.org/download-your-cover/"

# Fastly CDNs
fastly_service_ids = ['3M35rb7puabccOLrFFxy2']
fastly_api_key = 'fake_fastly_api_key'

elifepubmed_config_file = 'tests/activity/pubmed.cfg'
elifepubmed_config_section = 'elife'

elifecrossref_config_file = 'tests/activity/crossref.cfg'
elifecrossref_config_section = 'elife'

big_query_project_id = ''

letterparser_config_file = 'tests/activity/letterparser.cfg'
letterparser_config_section = 'elife'
