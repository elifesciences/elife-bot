import boto3
from moto import mock_aws

swf_region = "antarctica"
domain = "test_domain"
default_task_list = "test_task_list"

storage_provider = "s3"
expanded_bucket = "origin_bucket"

publishing_buckets_prefix = ""
production_bucket = "production_bucket"

s3_session_bucket = "origin_bucket"

aws_access_key_id = "test_key_id"
aws_secret_access_key = "test_access_key"

lax_response_queue = "lax_response_queue"

workflow_starter_queue = "workflow_starter_queue"
sqs_region = ""
S3_monitor_queue = "incoming_queue"

redis_host = ""
redis_port = 6379
redis_db = 0
redis_expire_key = 86400  # seconds

ejp_bucket = "ejp_bucket"
ppp_cdn_bucket = "ppd_cdn_bucket"
archive_bucket = "archive_bucket"
bot_bucket = "bot_bucket"
lens_bucket = "dest_bucket"
poa_packaging_bucket = "poa_packaging_bucket"
poa_bucket = "poa_bucket"
poa_incoming_queue = "poa_incoming_queue"
ses_poa_sender_email = ""
ses_poa_recipient_email = ""

lax_article_endpoint = "https://test/eLife.{article_id}"
lax_article_versions = "https://test/eLife.{article_id}/version/"
lax_article_versions_accept_header = (
    "application/vnd.elife.article-history+json;version=2"
)
lax_article_related = "https://test/eLife.{article_id}/related"
verify_ssl = False
lax_auth_key = "an_auth_key"

digest_config_file = "tests/activity/digest.cfg"
digest_config_section = "elife"

digest_endpoint = "https://digests/{digest_id}"
digest_auth_key = "digest_auth_key"

no_download_extensions = "tif"

crossref_url = ""
crossref_login_id = ""
crossref_login_passwd = ""

# Logging
setLevel = "INFO"

git_repo_name = "elife-article-xml-ci"
git_repo_path = "articles/"
github_token = "1234567890abcdef"

# PDF cover
pdf_cover_generator = "https://localhost/personalised-covers/"
pdf_cover_landing_page = "https://localhost.org/download-your-cover/"

# Fastly CDNs
fastly_service_ids = ["3M35rb7puabccOLrFFxy2"]
fastly_api_key = "fake_fastly_api_key"

elifepubmed_config_file = "tests/activity/pubmed.cfg"
elifepubmed_config_section = "elife"

elifecrossref_config_file = "tests/activity/crossref.cfg"
elifecrossref_config_section = "elife"

jatsgenerator_config_file = "tests/activity/jatsgenerator.cfg"
jatsgenerator_config_section = "elife"

big_query_project_id = ""

letterparser_config_file = "tests/activity/letterparser.cfg"
letterparser_config_section = "elife"

# DOAJ deposit settings
journal_eissn = "2050-084X"
doaj_url_link_pattern = "https://elifesciences.org/articles/{article_id}"
doaj_endpoint = "https://doaj/api/v2/articles"
doaj_api_key = ""

era_incoming_queue = "era_incoming_queue"

software_heritage_api_get_origin_pattern = (
    "https://archive.swh.example.org/api/1/origin/{origin}/get/"
)

accepted_submission_queue = "cleaning_queue"

downstream_recipients_yaml = "tests/downstreamRecipients.yaml"

publication_email_yaml = "tests/publicationEmail.yaml"

docmap_url_pattern = "https://example.org/path/get-by-manuscript-id?manuscript_id={article_id}"
docmap_account_id = "https://sciety.org/groups/elife"
docmap_index_url = "https://example.org/path/index"

# Mathpix settings
mathpix_endpoint = "https://api.mathpix.com.example.org/v3/text"
mathpix_app_id = "elife-bot"
mathpix_app_key = "key"

# EPP settings
epp_data_bucket = "epp_bucket"

# user-agent for using in requests
user_agent = "user_agent/version (https://example.org)"

meca_xsl_endpoint = "https://example.org/xsl"
meca_dtd_endpoint = "https://example.org/dtd"
meca_xsl_silent_endpoint = "https://example.org/silent-xsl"

preprint_issues_repo_name = "preprint-issues"

reviewed_preprint_api_endpoint = "https://api/path/{article_id}v{version}"


@mock_aws
def aws_conn(service, service_creation_kwargs):
    """this function is missing in the regular `settings.py` file because it is added dynamically by
    the `provider.get_settings` function.

    during testing this file is imported and used directly, bypassing `provider.get_settings` with no
    opportunity to either add it or patch it with `@mock_aws`.

    there is another mock `settings.py` file with the same function in `tests.activity.settings_mock.py`."""
    return boto3.client(service, **service_creation_kwargs)
