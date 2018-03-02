
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
event_monitor_queue = ""
sqs_region = ""


simpledb_region = ""
simpledb_domain_postfix = "_test"
ejp_bucket = 'ejp_bucket'
bot_bucket = 'bot_bucket'
lens_bucket = 'dest_bucket'
poa_packaging_bucket = 'poa_packaging_bucket'
poa_bucket = 'poa_bucket'
ses_poa_sender_email = ""
ses_poa_recipient_email = ""
ses_admin_email = ""
templates_bucket = ""
ppp_cdn_bucket = 'ppd_cdn_bucket'

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
pdf_cover_generator = "url_here"

iiif_resolver = ""
path_to_iiif_server = ""

no_download_extensions = "tif"

cloudfront_distribution_id_cdn = "DISTRIBUTIONID"

elifecrossref_config_file = 'tests/activity/crossref.cfg'
elifecrossref_config_section = 'elife'

HEFCE_FTP_URI = "hefce_ftp.localhost"
HEFCE_FTP_USERNAME = ""
HEFCE_FTP_PASSWORD = ""
HEFCE_FTP_CWD = ""
HEFCE_EMAIL = ""

HEFCE_SFTP_URI = "hefce_sftp.localhost"
HEFCE_SFTP_USERNAME = ""
HEFCE_SFTP_PASSWORD = ""
HEFCE_SFTP_CWD = ""
HEFCE_EMAIL = ""

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

git_repo_name = 'elife-article-xml-ci'
git_repo_path = '/articles/'
github_token = '1234567890abcdef'

PUBMED_FTP_URI = ""
PUBMED_FTP_USERNAME = ""
PUBMED_FTP_PASSWORD = ""
PUBMED_FTP_CWD = ""

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
