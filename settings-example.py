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
    aws_access_key_id = '<your access key>'
    aws_secret_access_key = '<your secret key>'

    workflow_context_path = 'workflow-context/'

    # SQS settings
    sqs_region = 'eu-west-1'
    S3_monitor_queue = 'xxawsxx-incoming-queue'
    event_monitor_topic = 'arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--exp'
    event_monitor_queue = 'exp-event-property-incoming-queue'
    workflow_starter_queue = 'exp-workflow-starter-queue'
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = 'exp-'
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = 's3-eu-west-1.amazonaws.com'
    production_bucket = 'elife-production-final'
    expanded_bucket = 'elife-publishing-expanded'
    ppp_cdn_bucket = 'elife-published/articles'
    digest_cdn_bucket = 'elife-published/digests'
    archive_bucket = 'elife-publishing-archive'

    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = 'http://gateway.internal/articles/{article_id}/versions'
    verify_ssl = True  # False when testing

    no_download_extensions = 'tif'

    # end PPP settings

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

    # SMTP settings
    smtp_host = 'localhost'
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = 'elife-lens-dev'

    # Lens jpg bucket
    lens_jpg_bucket = "exp-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot-dev'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery-dev'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging-dev'

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Digest email settings
    digest_config_file = 'digest.cfg'
    digest_config_section = 'elife'
    digest_sender_email = "sender@example.org"
    digest_recipient_email = ["e@example.org", "life@example.org"]
    digest_error_recipient_email = "error@example.org"
    digest_medium_recipient_email = ["e@example.org", "life@example.org"]

    # digest endpoint
    digest_endpoint = 'https://digests/{digest_id}'
    digest_auth_key = 'digest_auth_key'

    # digest typesetter endpoint
    typesetter_digest_endpoint = 'https://typesetter/updateDigest'
    typesetter_digest_api_key = 'typesetter_api_key'

    # journal preview
    journal_preview_base_url = 'https://preview--journal.example.org'

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = 'elife-ejp-ftp-dev'

    # Templates S3 settings
    templates_bucket = 'elife-bot-dev'

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # Crossref generation
    elifecrossref_config_file = 'crossref.cfg'
    elifecrossref_config_section = 'elife'

    # Crossref
    crossref_url = 'http://test.crossref.org/servlet/deposit'
    crossref_login_id = ''
    crossref_login_passwd = ''

    # PubMed generation
    elifepubmed_config_file = 'pubmed.cfg'
    elifepubmed_config_section = 'elife'

    # PoA generation
    jatsgenerator_config_file = 'jatsgenerator.cfg'
    jatsgenerator_config_section = 'elife'
    packagepoa_config_file = 'packagepoa.cfg'
    packagepoa_config_section = 'elife'

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
    HEFCE_EMAIL = "hefce@example.org"

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
    SCOPUS_EMAIL = "scopus@example.org"

    # Scopus SFTP settings
    SCOPUS_SFTP_URI = ""
    SCOPUS_SFTP_USERNAME = ""
    SCOPUS_SFTP_PASSWORD = ""
    SCOPUS_SFTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""
    WOS_EMAIL = "wos@example.org"

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # CNKI FTP settings
    CNKI_FTP_URI = ""
    CNKI_FTP_USERNAME = ""
    CNKI_FTP_PASSWORD = ""
    CNKI_FTP_CWD = ""
    CNKI_EMAIL = "cnki@example.org"

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"
    s3_session_bucket = "exp-elife-bot-sessions"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    # Version control for xml
    github_token = "tokenhere"
    git_repo_name = "repository-name"
    git_repo_path = "/articles/"

    # eLife 2.0 bot lax communication settings
    xml_info_queue = "bot-lax-exp-inc"
    lax_response_queue = "bot-lax-exp-out"
    # eLife 2.0 transition settings
    publication_authority = "journal"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # Fastly CDNs
    fastly_service_ids = ['3M35rb7puabccOLrFFxy2']
    fastly_api_key = 'fake_fastly_api_key'

    article_path_pattern = "/articles/{id}v{version}"


class dev():
    # AWS settings
    aws_access_key_id = '<your access key>'
    aws_secret_access_key = '<your secret key>'

    workflow_context_path = 'workflow-context/'

    # SQS settings
    sqs_region = 'eu-west-1'
    S3_monitor_queue = 'xxawsxx-incoming-queue'
    event_monitor_topic = 'arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--dev'
    event_monitor_queue = 'dev-event-property-incoming-queue'
    workflow_starter_queue = 'dev-workflow-starter-queue'
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = 'dev-'
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = 's3-eu-west-1.amazonaws.com'
    production_bucket = 'elife-production-final'
    expanded_bucket = 'elife-publishing-expanded'
    ppp_cdn_bucket = 'elife-published/articles'
    digest_cdn_bucket = 'elife-published/digests'
    archive_bucket = 'elife-publishing-archive'

    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = 'http://gateway.internal/articles/{article_id}/versions'
    verify_ssl = True  # False when testing

    no_download_extensions = 'tif'

    # end PPP settings

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

    # SMTP settings
    smtp_host = 'localhost'
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = 'elife-lens-dev'

    # Lens jpg bucket
    lens_jpg_bucket = "dev-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot-dev'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery-dev'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging-dev'

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Digest email settings
    digest_config_file = 'digest.cfg'
    digest_config_section = 'elife'
    digest_sender_email = "sender@example.org"
    digest_recipient_email = ["e@example.org", "life@example.org"]
    digest_error_recipient_email = "error@example.org"
    digest_medium_recipient_email = ["e@example.org", "life@example.org"]

    # digest endpoint
    digest_endpoint = 'https://digests/{digest_id}'
    digest_auth_key = 'digest_auth_key'

    # digest typesetter endpoint
    typesetter_digest_endpoint = 'https://typesetter/updateDigest'
    typesetter_digest_api_key = 'typesetter_api_key'

    # journal preview
    journal_preview_base_url = 'https://preview--journal.example.org'

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = 'elife-ejp-ftp-dev'

    # Templates S3 settings
    templates_bucket = 'elife-bot-dev'

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # Crossref generation
    elifecrossref_config_file = 'crossref.cfg'
    elifecrossref_config_section = 'elife'

    # Crossref
    crossref_url = 'http://test.crossref.org/servlet/deposit'
    crossref_login_id = ''
    crossref_login_passwd = ''

    # PubMed generation
    elifepubmed_config_file = 'pubmed.cfg'
    elifepubmed_config_section = 'elife'

    # PoA generation
    jatsgenerator_config_file = 'jatsgenerator.cfg'
    jatsgenerator_config_section = 'elife'
    packagepoa_config_file = 'packagepoa.cfg'
    packagepoa_config_section = 'elife'

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
    HEFCE_EMAIL = "hefce@example.org"

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
    SCOPUS_EMAIL = "scopus@example.org"

    # Scopus SFTP settings
    SCOPUS_SFTP_URI = ""
    SCOPUS_SFTP_USERNAME = ""
    SCOPUS_SFTP_PASSWORD = ""
    SCOPUS_SFTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""
    WOS_EMAIL = "wos@example.org"

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # CNKI FTP settings
    CNKI_FTP_URI = ""
    CNKI_FTP_USERNAME = ""
    CNKI_FTP_PASSWORD = ""
    CNKI_FTP_CWD = ""
    CNKI_EMAIL = "cnki@example.org"

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"
    s3_session_bucket = "dev-elife-bot-sessions"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    # Version control for xml
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

    # Fastly CDNs
    fastly_service_ids = ['3M35rb7puabccOLrFFxy2']
    fastly_api_key = 'fake_fastly_api_key'

    article_path_pattern = "/articles/{id}v{version}"


class live():
    # AWS settings
    aws_access_key_id = '<your access key>'
    aws_secret_access_key = '<your secret key>'

    workflow_context_path = 'workflow-context/'

    # SQS settings
    sqs_region = 'eu-west-1'
    S3_monitor_queue = 'incoming-queue'
    event_monitor_topic = 'arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--prod'
    event_monitor_queue = 'event-property-incoming-queue'
    workflow_starter_queue = 'workflow-starter-queue'
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = ''
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = 's3-eu-west-1.amazonaws.com'
    production_bucket = 'elife-production-final'
    expanded_bucket = 'elife-publishing-expanded'
    # since prefix is empty
    ppp_cdn_bucket = 'prod-elife-published/articles'
    digest_cdn_bucket = 'prod-elife-published/digests'
    archive_bucket = 'prod-elife-publishing-archive'

    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = 'http://gateway.internal/articles/{article_id}/versions'
    verify_ssl = True  # False when testing

    no_download_extensions = 'tif'

    # end PPP settings

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

    # SMTP settings
    smtp_host = 'localhost'
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = 'elife-lens'

    # Lens jpg bucket
    lens_jpg_bucket = "elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = 'elife-bot'

    # POA delivery bucket
    poa_bucket = 'elife-ejp-poa-delivery'

    # POA packaging bucket
    poa_packaging_bucket = 'elife-poa-packaging'

    # Article subjects data
    article_subjects_data_bucket = "elife-bot/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # PMC email settings
    ses_pmc_sender_email = "sender@example.com"
    ses_pmc_recipient_email = "admin@example.com"
    ses_pmc_revision_recipient_email = "sender@example.com"

    # Digest email settings
    digest_config_file = 'digest.cfg'
    digest_config_section = 'elife'
    digest_sender_email = "sender@example.org"
    digest_recipient_email = ["e@example.org", "life@example.org"]
    digest_error_recipient_email = "error@example.org"
    digest_medium_recipient_email = ["e@example.org", "life@example.org"]

    # digest endpoint
    digest_endpoint = 'https://digests/{digest_id}'
    digest_auth_key = 'digest_auth_key'

    # digest typesetter endpoint
    typesetter_digest_endpoint = 'https://typesetter/updateDigest'
    typesetter_digest_api_key = 'typesetter_api_key'

    # journal preview
    journal_preview_base_url = 'https://preview--journal.example.org'

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = 'elife-ejp-ftp'

    # Templates S3 settings
    templates_bucket = 'elife-bot'

    # Crossref generation
    elifecrossref_config_file = 'crossref.cfg'
    elifecrossref_config_section = 'elife'

    # Crossref
    crossref_url = 'http://doi.crossref.org/servlet/deposit'
    crossref_login_id = ''
    crossref_login_passwd = ''

    # PubMed generation
    elifepubmed_config_file = 'pubmed.cfg'
    elifepubmed_config_section = 'elife'

    # PoA generation
    jatsgenerator_config_file = 'jatsgenerator.cfg'
    jatsgenerator_config_section = 'elife'
    packagepoa_config_file = 'packagepoa.cfg'
    packagepoa_config_section = 'elife'

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
    HEFCE_EMAIL = "hefce@example.org"

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
    SCOPUS_EMAIL = "scopus@example.org"

    # Scopus SFTP settings
    SCOPUS_SFTP_URI = ""
    SCOPUS_SFTP_USERNAME = ""
    SCOPUS_SFTP_PASSWORD = ""
    SCOPUS_SFTP_CWD = ""

    # Web of Science WoS FTP settings
    WOS_FTP_URI = ""
    WOS_FTP_USERNAME = ""
    WOS_FTP_PASSWORD = ""
    WOS_FTP_CWD = ""
    WOS_EMAIL = "wos@example.org"

    # CNPIEC FTP settings
    CNPIEC_FTP_URI = ""
    CNPIEC_FTP_USERNAME = ""
    CNPIEC_FTP_PASSWORD = ""
    CNPIEC_FTP_CWD = ""

    # CNKI FTP settings
    CNKI_FTP_URI = ""
    CNKI_FTP_USERNAME = ""
    CNKI_FTP_PASSWORD = ""
    CNKI_FTP_CWD = ""
    CNKI_EMAIL = "cnki@example.org"

    # Logging
    setLevel = "INFO"

    # Session
    session_class = "RedisSession"
    s3_session_bucket = "prod-elife-bot-sessions"

    # Redis
    redis_host = "127.0.0.1"
    redis_port = 6379
    redis_db = 0
    redis_expire_key = 86400  # seconds

    # Version control for xml
    github_token = "tokenhere"
    git_repo_name = "elife-articles-xml"
    git_repo_path = "/articles/"

    # eLife 2.0 bot lax communication settings
    xml_info_queue = "bot-lax-prod-inc"
    lax_response_queue = "bot-lax-prod-out"
    # eLife 2.0 transition settings
    publication_authority = "journal"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # Fastly CDNs
    fastly_service_ids = ['3M35rb7puabccOLrFFxy2']
    fastly_api_key = 'fake_fastly_api_key'

    article_path_pattern = "/articles/{id}v{version}"


def get_settings(ENV="dev"):
    """
    Return the settings class based on the environment type provided,
    by default use the dev environment settings
    """
    return eval(ENV)
