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


class exp():
    # AWS settings
    # aws_access_key_id = ''
    aws_secret_access_key = ''

    workflow_context_path = 'workflow-context/'

    # SQS settings
    # sqs_region = 'eu-west-1'
    S3_monitor_queue = 'xxawsxx-incoming-queue'
    event_monitor_queue = 'event-property-incoming-queue'
    workflow_starter_queue = 'workflow-starter-queue'
    website_ingest_queue = 'website-ingest-queue'
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # Storage settings
    storage_provider = "s3"

    # S3 settings
    publishing_buckets_prefix = 'jr-'
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = 's3-eu-west-1.amazonaws.com'
    production_bucket = 'elife-production-final'
    eif_bucket = 'elife-publishing-eif'
    expanded_bucket = 'elife-publishing-expanded'
    ppp_cdn_bucket = 'elife-publishing-cdn'
    archive_bucket = 'elife-publishing-archive'
    xml_bucket = 'elife-publishing-xml'

    # REST endpoint for drupal node builder
    # drupal_naf_endpoint = 'http://localhost:5000/nodes'
    drupal_EIF_endpoint = 'http://52.4.182.179/api/article.json'
    drupal_approve_endpoint = 'http://52.2.70.162/api/publish/'
    drupal_update_user = ''
    drupal_update_pass = ''

    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = 'http://2015-09-03.lax.elifesciences.org/api/v1/article/10.7554/eLife.{article_id}/version/'
    lax_update = 'http://2015-09-03.lax.elifesciences.org/api/v1/import/article/'
    lax_update_user = ''
    lax_update_pass = ''
    verify_ssl = True # False when testing

    no_download_extensions = 'tif'

    # end JR settings

    # S3 settings
    bucket = 'elife-articles'
    prefix = ''
    delimiter = '/'

    # SWF queue settings
    domain = "Publish.dev"
    default_task_list = "DefaultTaskList"

    # SimpleDB settings
    simpledb_region = "eu-west-1"
    simpledb_domain_postfix = "_dev"

    # SES settings
    # email needs to be verified by AWS
    ses_region = "eu-west-1"
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

    # Lens jpg bucket
    lens_jpg_bucket = "exp-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot-dev'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery-dev'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging-dev'

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

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

    # PMC FTP settings
    PMC_FTP_URI = ""
    PMC_FTP_USERNAME = ""
    PMC_FTP_PASSWORD = ""
    PMC_FTP_CWD = ""

    # HEFCE Archive FTP settings
    HEFCE_FTP_URI = ""
    HEFCE_FTP_USERNAME = ""
    HEFCE_FTP_PASSWORD = ""
    HEFCE_FTP_CWD = ""

    # HEFCE Archive SFTP settings
    HEFCE_SFTP_URI = ""
    HEFCE_SFTP_USERNAME = ""
    HEFCE_SFTP_PASSWORD = ""
    HEFCE_SFTP_CWD = ""

    # GoOA FTP settings
    GOOA_FTP_URI = ""
    GOOA_FTP_USERNAME = ""
    GOOA_FTP_PASSWORD = ""
    GOOA_FTP_CWD = ""

    # Scopus FTP settings
    SCOPUS_FTP_URI = ""
    SCOPUS_FTP_USERNAME = ""
    SCOPUS_FTP_PASSWORD = ""
    SCOPUS_FTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    #Version control for xml
    github_token = "tokenhere"
    git_repo_name = "repository-name"
    git_repo_path = "/articles/"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    cloudfront_distribution_id_cdn = "DISTRIBUTIONID"


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

    # Lens jpg bucket
    lens_jpg_bucket = "exp-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot-dev'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery-dev'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging-dev'

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

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

    # PMC FTP settings
    PMC_FTP_URI = ""
    PMC_FTP_USERNAME = ""
    PMC_FTP_PASSWORD = ""
    PMC_FTP_CWD = ""

    # HEFCE Archive FTP settings
    HEFCE_FTP_URI = ""
    HEFCE_FTP_USERNAME = ""
    HEFCE_FTP_PASSWORD = ""
    HEFCE_FTP_CWD = ""

    # HEFCE Archive SFTP settings
    HEFCE_SFTP_URI = ""
    HEFCE_SFTP_USERNAME = ""
    HEFCE_SFTP_PASSWORD = ""
    HEFCE_SFTP_CWD = ""

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

    # Scopus FTP settings
    SCOPUS_FTP_URI = ""
    SCOPUS_FTP_USERNAME = ""
    SCOPUS_FTP_PASSWORD = ""
    SCOPUS_FTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    #Version control for xml
    github_token = "tokenhere"
    git_repo_name = "repository-name"
    git_repo_path = "/articles/"

    # videos
    video_url = "https://video.url.here/"

     # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # CloudFront
    cloudfront_distribution_id_cdn = "DISTRIBUTIONID"


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

    # Lens jpg bucket
    lens_jpg_bucket = "elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging'

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

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

    # PMC FTP settings
    PMC_FTP_URI = ""
    PMC_FTP_USERNAME = ""
    PMC_FTP_PASSWORD = ""
    PMC_FTP_CWD = ""

    # HEFCE Archive FTP settings
    HEFCE_FTP_URI = ""
    HEFCE_FTP_USERNAME = ""
    HEFCE_FTP_PASSWORD = ""
    HEFCE_FTP_CWD = ""

    # HEFCE Archive SFTP settings
    HEFCE_SFTP_URI = ""
    HEFCE_SFTP_USERNAME = ""
    HEFCE_SFTP_PASSWORD = ""
    HEFCE_SFTP_CWD = ""

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
    
    # Scopus FTP settings
    SCOPUS_FTP_URI = ""
    SCOPUS_FTP_USERNAME = ""
    SCOPUS_FTP_PASSWORD = ""
    SCOPUS_FTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    #Version control for xml
    github_token = "tokenhere"
    git_repo_name = "elife-articles-xml"
    git_repo_path = "/articles/"

    # videos
    video_url = "https://video.url.here/"

     # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # CloudFront
    cloudfront_distribution_id_cdn = "DISTRIBUTIONID"


def get_settings(ENV="dev"):
    """
    Return the settings class based on the environment type provided,
    by default use the dev environment settings
    """
    return eval(ENV)
