class test():
    # AWS settings
    aws_access_key_id = ''
    aws_secret_access_key = ''

    workflow_context_path = ''

    # SQS settings
    sqs_region = ''
    S3_monitor_queue = ''
    event_monitor_queue = ''
    workflow_starter_queue = ''
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # S3 settings
    publishing_buckets_prefix = ''
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = ''
    production_bucket = ''
    eif_bucket = 'dest_bucket'
    expanded_bucket = 'origin_bucket'
    ppp_cdn_bucket = ''
    archive_bucket = ''
    xml_bucket = ''

    # REST endpoint for drupal node builder
    # drupal_naf_endpoint = 'http://localhost:5000/nodes'
    drupal_EIF_endpoint = ''
    drupal_approve_endpoint = ''
    drupal_update_user = ''
    drupal_update_pass = ''

    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = ''
    lax_update = ''
    lax_update_user = ''
    lax_update_pass = ''

    no_download_extensions = 'tif'

    # end JR settings

    # S3 settings
    bucket = ''
    prefix = ''
    delimiter = '/'

    # SWF queue settings
    domain = ""
    default_task_list = ""

    # SimpleDB settings
    simpledb_region = ""
    simpledb_domain_postfix = ""

    # Converter settings
    converter_url = ""
    converter_token = ""

    # SES settings
    # email needs to be verified by AWS
    ses_region = ""
    ses_sender_email = ""
    ses_admin_email = ""

    # CDN bucket settings
    cdn_bucket = ''
    cdn_distribution_id = u''
    cdn_domain_name = ''

    # Lens bucket settings
    lens_bucket = ''
    lens_distribution_id = u''
    lens_domain_name = ''

    # Lens jpg bucket
    lens_jpg_bucket = ""

    # Bot S3 settings
    bot_bucket = ''

    # POA delivery bucket
    poa_bucket = ''

    # POA packaging bucket
    poa_packaging_bucket = ''

    # POA FTP settings
    POA_FTP_URI = ""
    POA_FTP_USERNAME = ""
    POA_FTP_PASSWORD = ""
    POA_FTP_CWD = ""

    # POA email settings
    ses_poa_sender_email = ""
    ses_poa_recipient_email = ""

    # PMC email settings
    ses_pmc_sender_email = ""
    ses_pmc_recipient_email = ""

    # EJP S3 settings
    ejp_bucket = ''

    # Templates S3 settings
    templates_bucket = ''

    # Crossref
    crossref_url = ''
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

    # Logging
    setLevel = "INFO"



def get_settings(ENV="test"):
    """
    Return the settings class based on the environment type provided,
    by default use the dev environment settings
    """
    return eval(ENV)
