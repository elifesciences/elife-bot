import boto3
from moto import mock_aws

swf_region = ""
domain = ""
default_task_list = ""

storage_provider = "s3"
expanded_bucket = "origin_bucket"

publishing_buckets_prefix = ""
production_bucket = "origin_bucket"
ppp_cdn_bucket = ""
preprint_cdn_bucket = "published/preprints"

archive_bucket = "archive_bucket"

aws_access_key_id = ""
aws_secret_access_key = ""

workflow_starter_queue = ""
event_monitor_queue = ""
sqs_region = ""

redis_host = ""
redis_port = 6379
redis_db = 0
redis_expire_key = 86400  # seconds

ejp_bucket = "ejp_bucket"
bot_bucket = "bot_bucket"
lens_bucket = "dest_bucket"
poa_packaging_bucket = "poa_packaging_bucket"
poa_bucket = "poa_bucket"
ses_sender_email = ""
ses_poa_sender_email = "sender@example.org"
ses_poa_recipient_email = ""
ses_admin_email = ""
ses_bcc_recipient_email = ""
email_templates_path = "tests/test_data/templates"
ppp_cdn_bucket = "ppd_cdn_bucket"
digest_cdn_bucket = "ppd_cdn_bucket/digests"

lax_article_versions = "https://test/eLife.{article_id}/version/"
lax_article_related = "https://test/eLife.{article_id}/related"
verify_ssl = False
lax_auth_key = "an_auth_key"

PMC_FTP_URI = "pmc.localhost"
PMC_FTP_USERNAME = ""
PMC_FTP_PASSWORD = ""
PMC_FTP_CWD = ""

digest_config_file = "tests/activity/digest.cfg"
digest_config_section = "elife"
digest_sender_email = "sender@example.org"
# recipients of digest validation error emails
digest_validate_error_recipient_email = "error@example.org"
# recipients of digest docx email attachment
digest_docx_recipient_email = ["e@example.org", "life@example.org"]
# recipients of post digest to endpoint emails and error emails
digest_jats_recipient_email = ["e@example.org", "life@example.org"]
digest_jats_error_recipient_email = "error@example.org"
# recipients of digest medium post created emails
digest_medium_recipient_email = ["e@example.org", "life@example.org"]

digest_endpoint = "https://digests/{digest_id}"
digest_auth_key = "digest_auth_key"

typesetter_digest_endpoint = "https://typesetter/updateDigest"
typesetter_digest_api_key = "typesetter_api_key"
typesetter_digest_account_key = "1"

ftp_deposit_error_sender_email = "sender@example.org"
ftp_deposit_error_recipient_email = ["e@example.org", "life@example.org"]

journal_preview_base_url = "https://preview"

features_publication_recipient_email = "features_team@example.org"
email_video_recipient_email = "features_team@example.org"

xml_info_queue = "test-elife-xml-info"

video_url = "https://videometadata/"

crossref_url = ""
crossref_login_id = ""
crossref_login_passwd = ""

# PDF cover
pdf_cover_generator = "url_here"

iiif_resolver = ""
path_to_iiif_server = ""

no_download_extensions = "tif"

elifecrossref_config_file = "tests/activity/crossref.cfg"
elifecrossref_config_section = "elife"
elifecrossref_preprint_config_section = "elife_preprint"
elifecrossref_preprint_version_config_section = "elife_preprint_version"

jatsgenerator_config_file = "tests/activity/jatsgenerator.cfg"
jatsgenerator_config_section = "elife"

packagepoa_config_file = "tests/activity/packagepoa.cfg"
packagepoa_config_section = "elife"

HEFCE_FTP_URI = "hefce_ftp.localhost"
HEFCE_FTP_USERNAME = ""
HEFCE_FTP_PASSWORD = ""
HEFCE_FTP_CWD = ""
HEFCE_EMAIL = ["", ""]

HEFCE_SFTP_URI = "hefce_sftp.localhost:22"
HEFCE_SFTP_USERNAME = ""
HEFCE_SFTP_PASSWORD = ""
HEFCE_SFTP_CWD = ""

CENGAGE_FTP_URI = "cengage.localhost"
CENGAGE_FTP_USERNAME = ""
CENGAGE_FTP_PASSWORD = ""
CENGAGE_FTP_CWD = ""
CENGAGE_EMAIL = "cengage@example.org"

GOOA_FTP_URI = "gooa.localhost"
GOOA_FTP_USERNAME = ""
GOOA_FTP_PASSWORD = ""
GOOA_FTP_CWD = ""

WOS_FTP_URI = "wos.localhost"
WOS_FTP_USERNAME = ""
WOS_FTP_PASSWORD = ""
WOS_FTP_CWD = ""
WOS_EMAIL = ""

CNPIEC_FTP_URI = "cnpiec.localhost"
CNPIEC_FTP_USERNAME = ""
CNPIEC_FTP_PASSWORD = ""
CNPIEC_FTP_CWD = ""

CNKI_FTP_URI = "cnki.localhost"
CNKI_FTP_USERNAME = ""
CNKI_FTP_PASSWORD = ""
CNKI_FTP_CWD = ""

CLOCKSS_FTP_URI = "clockss.localhost"
CLOCKSS_FTP_USERNAME = ""
CLOCKSS_FTP_PASSWORD = ""
CLOCKSS_FTP_CWD = ""

CLOCKSS_PREPRINT_FTP_URI = "clockss_preprint.localhost"
CLOCKSS_PREPRINT_FTP_USERNAME = ""
CLOCKSS_PREPRINT_FTP_PASSWORD = ""
CLOCKSS_PREPRINT_FTP_CWD = ""
CLOCKSS_PREPRINT_EMAIL = "clockss@example.org"

OVID_FTP_URI = "ovid.localhost"
OVID_FTP_USERNAME = ""
OVID_FTP_PASSWORD = ""
OVID_FTP_CWD = ""

ZENDY_SFTP_URI = "zendy.localhost:22"
ZENDY_SFTP_USERNAME = ""
ZENDY_SFTP_PASSWORD = ""
ZENDY_SFTP_CWD = ""
ZENDY_EMAIL = ""

OASWITCHBOARD_SFTP_URI = "oaswitchboard.localhost:22"
OASWITCHBOARD_SFTP_USERNAME = ""
OASWITCHBOARD_SFTP_PASSWORD = ""
OASWITCHBOARD_SFTP_CWD = ""
OASWITCHBOARD_EMAIL = ""

SCILIT_SFTP_URI = "scilit.localhost:22"
SCILIT_SFTP_USERNAME = ""
SCILIT_SFTP_PASSWORD = ""
SCILIT_SFTP_CWD = ""
SCILIT_EMAIL = ""

git_repo_name = "elife-article-xml-ci"
git_repo_path = "articles/"
github_token = "1234567890abcdef"
git_preprint_repo_path = "preprints/"
github_named_user = "github_user_name"

PUBMED_SFTP_URI = "pubmed.localhost:22"
PUBMED_SFTP_USERNAME = ""
PUBMED_SFTP_PASSWORD = ""
PUBMED_SFTP_CWD = ""

# PDF cover
pdf_cover_landing_page = "https://localhost.org/download-your-cover/"
pdf_cover_generator = "https://localhost/personalised-covers/"

elifepubmed_config_file = "tests/activity/pubmed.cfg"
elifepubmed_config_section = "elife"

# Article path
article_path_pattern = "/articles/{id}v{version}"

# Article subjects data
article_subjects_data_bucket = "bucket_name/modify_article_subjects"
article_subjects_data_file = "article_subjects.csv"

smtp_host = ""
smtp_port = ""
smtp_starttls = False
smtp_ssl = False
smtp_username = None
smtp_password = None

big_query_project_id = ""

letterparser_config_file = "tests/activity/letterparser.cfg"
letterparser_config_section = "elife"
decision_letter_sender_email = "sender@example.org"
decision_letter_validate_error_recipient_email = "error@example.org"
decision_letter_output_bucket = "dev-elife-bot-decision-letter-output"
decision_letter_bucket_folder_name_pattern = "elife{manuscript:0>5}"
decision_letter_xml_file_name_pattern = "elife-{manuscript:0>5}.xml"

typesetter_decision_letter_endpoint = "https://typesetter/updatedigest"
typesetter_decision_letter_api_key = "typesetter_api_key"
typesetter_decision_letter_account_key = "1"
decision_letter_jats_recipient_email = ["e@example.org", "life@example.org"]
decision_letter_jats_error_recipient_email = "error@example.org"

# DOAJ deposit settings
journal_eissn = "2050-084X"
doaj_url_link_pattern = "https://elifesciences.org/articles/{article_id}"
doaj_endpoint = "https://doaj/api/v2/articles"
doaj_api_key = ""

# Software Heritage deposit settings
software_heritage_deposit_endpoint = "https://deposit.swh.example.org/1"
software_heritage_collection_name = "elife"
software_heritage_auth_user = "user"
software_heritage_auth_pass = "pass"
software_heritage_api_get_origin_pattern = (
    "https://archive.swh.example.org/api/1/origin/{origin}/get/"
)

# Accepted submission workflow
accepted_submission_output_bucket = "accepted-submission-cleaning-output"
accepted_submission_sender_email = "sender@example.org"
accepted_submission_validate_error_recipient_email = "errors@example.org"
accepted_submission_output_recipient_email = "typesetter@example.org"

# Glencoe video deposit FTP settings
GLENCOE_FTP_URI = "glencoe.localhost"
GLENCOE_FTP_USERNAME = "user"
GLENCOE_FTP_PASSWORD = "pass"
GLENCOE_FTP_CWD = "folder"

downstream_recipients_yaml = "tests/downstreamRecipients.yaml"

publication_email_yaml = "tests/publicationEmail.yaml"

docmap_url_pattern = "https://example.org/path/get-by-manuscript-id?manuscript_id={article_id}"
docmap_account_id = "https://sciety.org/groups/elife"
docmap_index_url = "https://example.org/path/index"

assessment_terms_yaml = "tests/assessment_terms.yaml"

# Mathpix settings
mathpix_endpoint = "https://api.mathpix.com.example.org/v3/text"
mathpix_app_id = "elife-bot"
mathpix_app_key = "key"

# EPP settings
epp_data_bucket = "epp_bucket"

# Striking images bucket
striking_images_bucket = "striking_images_bucket"

# user-agent for using in requests
user_agent = "user_agent/version (https://example.org)"

meca_xsl_endpoint = "https://example.org/xsl"
meca_dtd_endpoint = "https://example.org/dtd"
meca_xsl_silent_endpoint = "https://example.org/silent-xsl"
preprint_schematron_endpoint = "https://example.org/schematron/preprint"

meca_bucket = "meca_bucket"

preprint_issues_repo_name = "preprint-issues"

external_meca_bucket_list = ["server-src-daily"]
meca_sts_role_arn = "arn:aws:iam:1234456789012/role:foo"
meca_sts_role_session_name = "bot"

reviewed_preprint_api_endpoint = "https://api/path/{article_id}v{version}"


@mock_aws
def aws_conn(service, service_creation_kwargs):
    """this function is missing in the regular `settings.py` file because it is added dynamically by
    the `provider.get_settings` function.

    during testing this file is imported and used directly, bypassing `provider.get_settings` with no
    opportunity to either add it or patch it with `@mock_aws`.

    there is another mock `settings.py` file with the same function in `tests.settings_mock.py`."""
    return boto3.client(service, **service_creation_kwargs)
