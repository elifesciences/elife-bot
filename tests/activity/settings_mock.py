
domain = ""
default_task_list = ""

storage_provider = 's3'
expanded_bucket = 'origin_bucket'

publishing_buckets_prefix = ""
production_bucket = "production_bucket"
ppp_cdn_bucket = ""

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

ejp_bucket = 'ejp_bucket'
bot_bucket = 'bot_bucket'
lens_bucket = 'dest_bucket'
poa_packaging_bucket = 'poa_packaging_bucket'
poa_bucket = 'poa_bucket'
ses_sender_email = ""
ses_poa_sender_email = ""
ses_poa_recipient_email = ""
ses_admin_email = ""
ses_bcc_recipient_email = ""
templates_bucket = ""
ppp_cdn_bucket = 'ppd_cdn_bucket'
digest_cdn_bucket = 'ppd_cdn_bucket/digests'

lax_article_versions = 'https://test/eLife.{article_id}/version/'
verify_ssl = False
lax_auth_key = 'an_auth_key'

PMC_FTP_URI = ""
PMC_FTP_USERNAME = ""
PMC_FTP_PASSWORD = ""
PMC_FTP_CWD = ""

digest_config_file = 'tests/activity/digest.cfg'
digest_config_section = 'elife'
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

digest_endpoint = 'https://digests/{digest_id}'
digest_auth_key = 'digest_auth_key'

typesetter_digest_endpoint = 'https://typesetter/updateDigest'
typesetter_digest_api_key = 'typesetter_api_key'
typesetter_digest_account_key = '1'

ftp_deposit_error_sender_email = "sender@example.org"
ftp_deposit_error_recipient_email = ["e@example.org", "life@example.org"]

journal_preview_base_url = 'https://preview'

features_publication_recipient_email = "features_team@example.org"
email_video_recipient_email = "features_team@example.org"

xml_info_queue = 'test-elife-xml-info'

video_url = ""

crossref_url = ""
crossref_login_id = ""
crossref_login_passwd = ""

# PDF cover
pdf_cover_generator = "url_here"

iiif_resolver = ""
path_to_iiif_server = ""

no_download_extensions = "tif"

elifecrossref_config_file = 'tests/activity/crossref.cfg'
elifecrossref_config_section = 'elife'

jatsgenerator_config_file = 'tests/activity/jatsgenerator.cfg'
jatsgenerator_config_section = 'elife'

packagepoa_config_file = 'tests/activity/packagepoa.cfg'
packagepoa_config_section = 'elife'

HEFCE_FTP_URI = "hefce_ftp.localhost"
HEFCE_FTP_USERNAME = ""
HEFCE_FTP_PASSWORD = ""
HEFCE_FTP_CWD = ""
HEFCE_EMAIL = ["", ""]

HEFCE_SFTP_URI = "hefce_sftp.localhost"
HEFCE_SFTP_USERNAME = ""
HEFCE_SFTP_PASSWORD = ""
HEFCE_SFTP_CWD = ""

CENGAGE_FTP_URI = "cengage.localhost"
CENGAGE_FTP_USERNAME = ""
CENGAGE_FTP_PASSWORD = ""
CENGAGE_FTP_CWD = ""
CENGAGE_EMAIL = ""

GOOA_FTP_URI = "gooa.localhost"
GOOA_FTP_USERNAME = ""
GOOA_FTP_PASSWORD = ""
GOOA_FTP_CWD = ""

SCOPUS_FTP_URI = "scopus_ftp.localhost"
SCOPUS_FTP_USERNAME = ""
SCOPUS_FTP_PASSWORD = ""
SCOPUS_FTP_CWD = ""
SCOPUS_EMAIL = ""

SCOPUS_SFTP_URI = "scopus_sftp.localhost"
SCOPUS_SFTP_USERNAME = ""
SCOPUS_SFTP_PASSWORD = ""
SCOPUS_SFTP_CWD = ""

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

OVID_FTP_URI = "ovid.localhost"
OVID_FTP_USERNAME = ""
OVID_FTP_PASSWORD = ""
OVID_FTP_CWD = ""

git_repo_name = 'elife-article-xml-ci'
git_repo_path = '/articles/'
github_token = '1234567890abcdef'

PUBMED_SFTP_URI = ""
PUBMED_SFTP_USERNAME = ""
PUBMED_SFTP_PASSWORD = ""
PUBMED_SFTP_CWD = ""

# PDF cover
pdf_cover_landing_page = "https://localhost.org/download-your-cover/"
pdf_cover_generator = "https://localhost/personalised-covers/"

elifepubmed_config_file = 'tests/activity/pubmed.cfg'
elifepubmed_config_section = 'elife'

# Article path
article_path_pattern = "/articles/{id}v{version}"

# Article subjects data
article_subjects_data_bucket = "bucket_name/modify_article_subjects"
article_subjects_data_file = "article_subjects.csv"

smtp_host = ''
smtp_port = ''
smtp_starttls = False
smtp_ssl = False
smtp_username = None
smtp_password = None

big_query_project_id = ''

letterparser_config_file = 'tests/activity/letterparser.cfg'
letterparser_config_section = 'elife'
decision_letter_sender_email = 'sender@example.org'
decision_letter_validate_error_recipient_email = 'error@example.org'
decision_letter_output_bucket = 'dev-elife-bot-decision-letter-output'
decision_letter_bucket_folder_name_pattern = 'elife{manuscript:0>5}'
decision_letter_xml_file_name_pattern = 'elife-{manuscript:0>5}.xml'

typesetter_decision_letter_endpoint = 'https://typesetter/decisionLetter'
typesetter_decision_letter_api_key = 'typesetter_api_key'
typesetter_decision_letter_account_key = '1'
decision_letter_jats_recipient_email = ["e@example.org", "life@example.org"]
decision_letter_jats_error_recipient_email = "error@example.org"
