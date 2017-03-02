
domain = ""
default_task_list = ""

bucket = "old_articles_bucket"

storage_provider = 's3'
eif_bucket = 'dest_bucket'
expanded_bucket = 'origin_bucket'

publishing_buckets_prefix = ""
production_bucket = "production_bucket"
ppp_cdn_bucket = ""

archive_bucket = "archive_bucket"

aws_access_key_id = ""
aws_secret_access_key = ""

workflow_starter_queue = ""
website_ingest_queue = ""
event_monitor_queue = ""
sqs_region = ""


simpledb_region = ""
simpledb_domain_postfix = "_test"
ejp_bucket = 'ejp_bucket'
bot_bucket = 'bot_bucket'
poa_packaging_bucket = 'poa_packaging_bucket'
poa_bucket = 'poa_bucket'
ses_poa_sender_email = ""
ses_poa_recipient_email = ""
templates_bucket = ""

drupal_EIF_endpoint = "https://website/api/article.json"
drupal_approve_endpoint = "https://website/api/publish/"
drupal_update_user = ""
drupal_update_pass = ""

lax_article_versions = 'https://test/eLife.{article_id}/version/'
verify_ssl = False

PMC_FTP_URI = ""
PMC_FTP_USERNAME = ""
PMC_FTP_PASSWORD = ""
PMC_FTP_CWD = ""

ses_pmc_sender_email = ""
ses_pmc_recipient_email = ""
ses_pmc_revision_recipient_email = ["e@example.org", "life@example.org"]

features_publication_recipient_email = "features_team@example.org"
publication_authority = ""
consider_Lax_elife_2_0 = True

xml_info_queue = 'test-elife-xml-info'

video_url = ""

# PDF cover
pdf_cover_generator = ""

iiif_resolver = ""
path_to_iiif_server = ""