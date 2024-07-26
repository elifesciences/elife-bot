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


class exp:
    # AWS settings
    aws_access_key_id = "<your access key>"
    aws_secret_access_key = "<your secret key>"

    workflow_context_path = "workflow-context/"

    # SQS settings
    sqs_region = "eu-west-1"
    S3_monitor_queue = "xxawsxx-incoming-queue"
    event_monitor_topic = (
        "arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--exp"
    )
    event_monitor_queue = "exp-event-property-incoming-queue"
    workflow_starter_queue = "exp-workflow-starter-queue"
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = "exp-"
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = "s3-eu-west-1.amazonaws.com"
    production_bucket = "elife-production-final"
    expanded_bucket = "elife-publishing-expanded"
    ppp_cdn_bucket = "elife-published/articles"
    digest_cdn_bucket = "elife-published/digests"
    archive_bucket = "elife-publishing-archive"

    lax_article_endpoint = "http://gateway.internal/articles/{article_id}"
    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = "http://gateway.internal/articles/{article_id}/versions"
    lax_article_versions_accept_header = (
        "application/vnd.elife.article-history+json;version=2"
    )
    lax_article_related = "http://gateway.internal/articles/{article_id}/related"
    verify_ssl = True  # False when testing
    lax_auth_key = ""

    no_download_extensions = "tif"

    # end PPP settings

    # SWF queue settings
    swf_region = "us-east-1"
    domain = "Publish.dev"
    default_task_list = "DefaultTaskList"

    # SES settings
    # email needs to be verified by AWS
    ses_region = "eu-west-1"
    ses_sender_email = "sender@example.com"
    ses_admin_email = "admin@example.com"
    ses_bcc_recipient_email = ""

    # SMTP settings
    smtp_host = "localhost"
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = "elife-lens-dev"

    # Lens jpg bucket
    lens_jpg_bucket = "exp-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = "elife-bot-dev"

    # POA delivery bucket
    poa_bucket = "elife-ejp-poa-delivery-dev"

    # POA packaging bucket
    poa_packaging_bucket = "elife-poa-packaging-dev"

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # Digest email settings
    digest_config_file = "digest.cfg"
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

    # digest endpoint
    digest_endpoint = "https://digests/{digest_id}"
    digest_auth_key = "digest_auth_key"

    # digest typesetter endpoint
    typesetter_digest_endpoint = "https://typesetter/updatedigest"
    typesetter_digest_api_key = "typesetter_api_key"
    typesetter_digest_account_key = "1"

    # decision letter
    decision_letter_sender_email = "sender@example.org"
    decision_letter_validate_error_recipient_email = "error@example.org"
    decision_letter_output_bucket = "exp-elife-bot-decision-letter-output"
    decision_letter_bucket_folder_name_pattern = "elife{manuscript:0>5}"
    decision_letter_xml_file_name_pattern = "elife-{manuscript:0>5}.xml"
    typesetter_decision_letter_endpoint = "https://typesetter/updatedigest"
    typesetter_decision_letter_api_key = "typesetter_api_key"
    typesetter_decision_letter_account_key = "1"
    decision_letter_jats_recipient_email = ["e@example.org", "life@example.org"]
    decision_letter_jats_error_recipient_email = "error@example.org"

    # PMC or FTP sending error email settings
    ftp_deposit_error_sender_email = "sender@example.org"
    ftp_deposit_error_recipient_email = ["e@example.org", "life@example.org"]

    # journal preview
    journal_preview_base_url = "https://preview--journal.example.org"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = "elife-ejp-ftp-dev"

    # Templates settings
    email_templates_path = "/opt/elife-email-templates"

    # Crossref generation
    elifecrossref_config_file = "crossref.cfg"
    elifecrossref_config_section = "elife"
    elifecrossref_preprint_config_section = "elife_preprint"
    elifecrossref_preprint_version_config_section = "elife_preprint_version"

    # Crossref
    crossref_url = "http://test.crossref.org/servlet/deposit"
    crossref_login_id = ""
    crossref_login_passwd = ""

    # PubMed generation
    elifepubmed_config_file = "pubmed.cfg"
    elifepubmed_config_section = "elife"

    # PoA generation
    jatsgenerator_config_file = "jatsgenerator.cfg"
    jatsgenerator_config_section = "elife"
    packagepoa_config_file = "packagepoa.cfg"
    packagepoa_config_section = "elife"

    # Decision letter parser
    letterparser_config_file = "letterparser.cfg"
    letterparser_config_section = "elife"

    # PubMed SFTP settings
    PUBMED_SFTP_URI = ""
    PUBMED_SFTP_USERNAME = ""
    PUBMED_SFTP_PASSWORD = ""
    PUBMED_SFTP_CWD = ""

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

    # CLOCKSS FTP settings
    CLOCKSS_FTP_URI = ""
    CLOCKSS_FTP_USERNAME = ""
    CLOCKSS_FTP_PASSWORD = ""
    CLOCKSS_FTP_CWD = ""
    CLOCKSS_EMAIL = "clockss@example.org"

    # OVID FTP settings
    OVID_FTP_URI = ""
    OVID_FTP_USERNAME = ""
    OVID_FTP_PASSWORD = ""
    OVID_FTP_CWD = ""
    OVID_EMAIL = ""

    # Zendy SFTP settings
    ZENDY_SFTP_URI = ""
    ZENDY_SFTP_USERNAME = ""
    ZENDY_SFTP_PASSWORD = ""
    ZENDY_SFTP_CWD = ""
    ZENDY_EMAIL = ""

    # OA Switchboard SFTP settings
    OASWITCHBOARD_SFTP_URI = ""
    OASWITCHBOARD_SFTP_USERNAME = ""
    OASWITCHBOARD_SFTP_PASSWORD = ""
    OASWITCHBOARD_SFTP_CWD = ""
    OASWITCHBOARD_EMAIL = ""

    # Scilit SFTP settings
    SCILIT_SFTP_URI = ""
    SCILIT_SFTP_USERNAME = ""
    SCILIT_SFTP_PASSWORD = ""
    SCILIT_SFTP_CWD = ""
    SCILIT_EMAIL = ""

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
    git_repo_path = "articles/"

    # eLife 2.0 bot lax communication settings
    xml_info_queue = "bot-lax-exp-inc"
    lax_response_queue = "bot-lax-exp-out"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # Fastly CDNs
    fastly_service_ids = ["3M35rb7puabccOLrFFxy2"]
    fastly_api_key = "fake_fastly_api_key"

    article_path_pattern = "/articles/{id}v{version}"

    # BigQuery settings
    big_query_project_id = ""

    # DOAJ deposit settings
    journal_eissn = ""
    doaj_url_link_pattern = "https://example.org/articles/{article_id}"
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

    # ERA article incoming queue
    era_incoming_queue = "exp-era-incoming-queue"

    # Accepted submission workflow
    accepted_submission_output_bucket = (
        "exp-elife-bot-accepted-submission-cleaning-output"
    )
    accepted_submission_sender_email = "sender@example.org"
    accepted_submission_validate_error_recipient_email = ""
    accepted_submission_queue = ""
    accepted_submission_output_recipient_email = "e@example.org"

    # Glencoe video deposit FTP settings
    GLENCOE_FTP_URI = ""
    GLENCOE_FTP_USERNAME = ""
    GLENCOE_FTP_PASSWORD = ""
    GLENCOE_FTP_CWD = ""

    downstream_recipients_yaml = "downstreamRecipients.yaml"

    publication_email_yaml = "publicationEmail.yaml"

    docmap_url_pattern = (
        "https://example.org/path/get-by-manuscript-id?manuscript_id={article_id}"
    )
    docmap_account_id = "https://sciety.org/groups/elife"
    docmap_index_url = "https://example.org/path/index"

    assessment_terms_yaml = "assessment_terms.yaml"

    # Mathpix settings
    mathpix_endpoint = ""
    mathpix_app_id = "elife-bot"
    mathpix_app_key = ""

    # EPP settings
    epp_data_bucket = "epp_bucket"

    # Striking images bucket
    striking_images_bucket = "striking_images_bucket"

    # user-agent for using in requests
    user_agent = "user_agent/version (https://example.org)"

    meca_xsl_endpoint = "https://example.org/xsl"
    meca_dtd_endpoint = "https://example.org/dtd"

    meca_bucket = "meca_bucket"


class dev:
    # AWS settings
    aws_access_key_id = "<your access key>"
    aws_secret_access_key = "<your secret key>"

    workflow_context_path = "workflow-context/"

    # SQS settings
    sqs_region = "eu-west-1"
    S3_monitor_queue = "xxawsxx-incoming-queue"
    event_monitor_topic = (
        "arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--dev"
    )
    event_monitor_queue = "dev-event-property-incoming-queue"
    workflow_starter_queue = "dev-workflow-starter-queue"
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = "dev-"
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = "s3-eu-west-1.amazonaws.com"
    production_bucket = "elife-production-final"
    expanded_bucket = "elife-publishing-expanded"
    ppp_cdn_bucket = "elife-published/articles"
    digest_cdn_bucket = "elife-published/digests"
    archive_bucket = "elife-publishing-archive"

    lax_article_endpoint = "http://gateway.internal/articles/{article_id}"
    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = "http://gateway.internal/articles/{article_id}/versions"
    lax_article_versions_accept_header = (
        "application/vnd.elife.article-history+json;version=2"
    )
    lax_article_related = "http://gateway.internal/articles/{article_id}/related"
    verify_ssl = True  # False when testing
    lax_auth_key = ""

    no_download_extensions = "tif"

    # end PPP settings

    # SWF queue settings
    swf_region = "us-east-1"
    domain = "Publish.dev"
    default_task_list = "DefaultTaskList"

    # SES settings
    # email needs to be verified by AWS
    ses_region = "us-east-1"
    ses_sender_email = "sender@example.com"
    ses_admin_email = "admin@example.com"
    ses_bcc_recipient_email = ""

    # SMTP settings
    smtp_host = "localhost"
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = "elife-lens-dev"

    # Lens jpg bucket
    lens_jpg_bucket = "dev-elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = "elife-bot-dev"

    # POA delivery bucket
    poa_bucket = "elife-ejp-poa-delivery-dev"

    # POA packaging bucket
    poa_packaging_bucket = "elife-poa-packaging-dev"

    # Article subjects data
    article_subjects_data_bucket = "elife-bot-dev/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # Digest email settings
    digest_config_file = "digest.cfg"
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

    # digest endpoint
    digest_endpoint = "https://digests/{digest_id}"
    digest_auth_key = "digest_auth_key"

    # digest typesetter endpoint
    typesetter_digest_endpoint = "https://typesetter/updatedigest"
    typesetter_digest_api_key = "typesetter_api_key"
    typesetter_digest_account_key = "1"

    # decision letter
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

    # PMC or FTP sending error email settings
    ftp_deposit_error_sender_email = "sender@example.org"
    ftp_deposit_error_recipient_email = ["e@example.org", "life@example.org"]

    # journal preview
    journal_preview_base_url = "https://preview--journal.example.org"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = "elife-ejp-ftp-dev"

    # Templates settings
    email_templates_path = "/opt/elife-email-templates"

    # Crossref generation
    elifecrossref_config_file = "crossref.cfg"
    elifecrossref_config_section = "elife"
    elifecrossref_preprint_config_section = "elife_preprint"
    elifecrossref_preprint_version_config_section = "elife_preprint_version"

    # Crossref
    crossref_url = "http://test.crossref.org/servlet/deposit"
    crossref_login_id = ""
    crossref_login_passwd = ""

    # PubMed generation
    elifepubmed_config_file = "pubmed.cfg"
    elifepubmed_config_section = "elife"

    # PoA generation
    jatsgenerator_config_file = "jatsgenerator.cfg"
    jatsgenerator_config_section = "elife"
    packagepoa_config_file = "packagepoa.cfg"
    packagepoa_config_section = "elife"

    # Decision letter parser
    letterparser_config_file = "letterparser.cfg"
    letterparser_config_section = "elife"

    # PubMed SFTP settings
    PUBMED_SFTP_URI = ""
    PUBMED_SFTP_USERNAME = ""
    PUBMED_SFTP_PASSWORD = ""
    PUBMED_SFTP_CWD = ""

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

    # CLOCKSS FTP settings
    CLOCKSS_FTP_URI = ""
    CLOCKSS_FTP_USERNAME = ""
    CLOCKSS_FTP_PASSWORD = ""
    CLOCKSS_FTP_CWD = ""
    CLOCKSS_EMAIL = "clockss@example.org"

    # OVID FTP settings
    OVID_FTP_URI = ""
    OVID_FTP_USERNAME = ""
    OVID_FTP_PASSWORD = ""
    OVID_FTP_CWD = ""
    OVID_EMAIL = ""

    # Zendy SFTP settings
    ZENDY_SFTP_URI = ""
    ZENDY_SFTP_USERNAME = ""
    ZENDY_SFTP_PASSWORD = ""
    ZENDY_SFTP_CWD = ""
    ZENDY_EMAIL = ""

    # OA Switchboard SFTP settings
    OASWITCHBOARD_SFTP_URI = ""
    OASWITCHBOARD_SFTP_USERNAME = ""
    OASWITCHBOARD_SFTP_PASSWORD = ""
    OASWITCHBOARD_SFTP_CWD = ""
    OASWITCHBOARD_EMAIL = ""

    # Scilit SFTP settings
    SCILIT_SFTP_URI = ""
    SCILIT_SFTP_USERNAME = ""
    SCILIT_SFTP_PASSWORD = ""
    SCILIT_SFTP_CWD = ""
    SCILIT_EMAIL = ""

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
    git_repo_path = "articles/"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # Fastly CDNs
    fastly_service_ids = ["3M35rb7puabccOLrFFxy2"]
    fastly_api_key = "fake_fastly_api_key"

    article_path_pattern = "/articles/{id}v{version}"

    # BigQuery settings
    big_query_project_id = ""

    # DOAJ deposit settings
    journal_eissn = ""
    doaj_url_link_pattern = "https://example.org/articles/{article_id}"
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

    # ERA article incoming queue
    era_incoming_queue = "dev-era-incoming-queue"

    # Accepted submission workflow
    accepted_submission_output_bucket = (
        "dev-elife-bot-accepted-submission-cleaning-output"
    )
    accepted_submission_sender_email = "sender@example.org"
    accepted_submission_validate_error_recipient_email = ""
    accepted_submission_queue = ""
    accepted_submission_output_recipient_email = "e@example.org"

    # Glencoe video deposit FTP settings
    GLENCOE_FTP_URI = ""
    GLENCOE_FTP_USERNAME = ""
    GLENCOE_FTP_PASSWORD = ""
    GLENCOE_FTP_CWD = ""

    downstream_recipients_yaml = "downstreamRecipients.yaml"

    publication_email_yaml = "publicationEmail.yaml"

    docmap_url_pattern = (
        "https://example.org/path/get-by-manuscript-id?manuscript_id={article_id}"
    )
    docmap_account_id = "https://sciety.org/groups/elife"
    docmap_index_url = "https://example.org/path/index"

    assessment_terms_yaml = "assessment_terms.yaml"

    # Mathpix settings
    mathpix_endpoint = ""
    mathpix_app_id = "elife-bot"
    mathpix_app_key = ""

    # EPP settings
    epp_data_bucket = "epp_bucket"

    # Striking images bucket
    striking_images_bucket = "striking_images_bucket"

    # user-agent for using in requests
    user_agent = "user_agent/version (https://example.org)"

    meca_xsl_endpoint = "https://example.org/xsl"
    meca_dtd_endpoint = "https://example.org/dtd"

    meca_bucket = "meca_bucket"


class live:
    # AWS settings
    aws_access_key_id = "<your access key>"
    aws_secret_access_key = "<your secret key>"

    workflow_context_path = "workflow-context/"

    # SQS settings
    sqs_region = "eu-west-1"
    S3_monitor_queue = "incoming-queue"
    event_monitor_topic = (
        "arn:aws:sns:eu-west-1:123456789012:elife-bot-event-property--prod"
    )
    event_monitor_queue = "event-property-incoming-queue"
    workflow_starter_queue = "workflow-starter-queue"
    workflow_starter_queue_pool_size = 5
    workflow_starter_queue_message_count = 5

    # PPP S3 settings
    storage_provider = "s3"
    publishing_buckets_prefix = ""
    # shouldn't need this but uploads seem to fail without. Should correspond with the s3 region
    # hostname list here http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region

    s3_hostname = "s3-eu-west-1.amazonaws.com"
    production_bucket = "elife-production-final"
    expanded_bucket = "elife-publishing-expanded"
    # since prefix is empty
    ppp_cdn_bucket = "prod-elife-published/articles"
    digest_cdn_bucket = "prod-elife-published/digests"
    archive_bucket = "prod-elife-publishing-archive"

    lax_article_endpoint = "http://gateway.internal/articles/{article_id}"
    # lax endpoint to retrieve information about published versions of articles
    lax_article_versions = "http://gateway.internal/articles/{article_id}/versions"
    lax_article_versions_accept_header = (
        "application/vnd.elife.article-history+json;version=2"
    )
    lax_article_related = "http://gateway.internal/articles/{article_id}/related"
    verify_ssl = True  # False when testing
    lax_auth_key = ""

    no_download_extensions = "tif"

    # end PPP settings

    # SWF queue settings
    swf_region = "us-east-1"
    domain = "Publish"
    default_task_list = "DefaultTaskList"

    # SES settings
    # email needs to be verified by AWS
    ses_region = "us-east-1"
    ses_sender_email = "sender@example.com"
    ses_admin_email = "admin@example.com"
    ses_bcc_recipient_email = ""

    # SMTP settings
    smtp_host = "localhost"
    smtp_port = 2525
    smtp_starttls = False
    smtp_ssl = False
    smtp_username = None
    smtp_password = None

    # Lens bucket settings
    lens_bucket = "elife-lens"

    # Lens jpg bucket
    lens_jpg_bucket = "elife-production-lens-jpg"

    # Bot S3 settings
    bot_bucket = "elife-bot"

    # POA delivery bucket
    poa_bucket = "elife-ejp-poa-delivery"

    # POA packaging bucket
    poa_packaging_bucket = "elife-poa-packaging"

    # Article subjects data
    article_subjects_data_bucket = "elife-bot/article_subjects_data"
    article_subjects_data_file = "article_subjects.csv"

    # POA email settings
    ses_poa_sender_email = "sender@example.com"
    ses_poa_recipient_email = "admin@example.com"

    # Digest email settings
    digest_config_file = "digest.cfg"
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

    # digest endpoint
    digest_endpoint = "https://digests/{digest_id}"
    digest_auth_key = "digest_auth_key"

    # digest typesetter endpoint
    typesetter_digest_endpoint = "https://typesetter/updatedigest"
    typesetter_digest_api_key = "typesetter_api_key"
    typesetter_digest_account_key = "1"

    # decision letter
    decision_letter_sender_email = "sender@example.org"
    decision_letter_validate_error_recipient_email = "error@example.org"
    decision_letter_output_bucket = "prod-elife-bot-decision-letter-output"
    decision_letter_bucket_folder_name_pattern = "elife{manuscript:0>5}"
    decision_letter_xml_file_name_pattern = "elife-{manuscript:0>5}.xml"
    typesetter_decision_letter_endpoint = "https://typesetter/updatedigest"
    typesetter_decision_letter_api_key = "typesetter_api_key"
    typesetter_decision_letter_account_key = "1"
    decision_letter_jats_recipient_email = ["e@example.org", "life@example.org"]
    decision_letter_jats_error_recipient_email = "error@example.org"

    # PMC or FTP sending error email settings
    ftp_deposit_error_sender_email = "sender@example.org"
    ftp_deposit_error_recipient_email = ["e@example.org", "life@example.org"]

    # journal preview
    journal_preview_base_url = "https://preview--journal.example.org"

    # Publication email settings
    features_publication_recipient_email = "features_team@example.com"

    # Email video article published settings
    email_video_recipient_email = "features_team@example.org"

    # EJP S3 settings
    ejp_bucket = "elife-ejp-ftp"

    # Templates settings
    email_templates_path = "/opt/elife-email-templates"

    # Crossref generation
    elifecrossref_config_file = "crossref.cfg"
    elifecrossref_config_section = "elife"
    elifecrossref_preprint_config_section = "elife_preprint"
    elifecrossref_preprint_version_config_section = "elife_preprint_version"

    # Crossref
    crossref_url = "http://doi.crossref.org/servlet/deposit"
    crossref_login_id = ""
    crossref_login_passwd = ""

    # PubMed generation
    elifepubmed_config_file = "pubmed.cfg"
    elifepubmed_config_section = "elife"

    # PoA generation
    jatsgenerator_config_file = "jatsgenerator.cfg"
    jatsgenerator_config_section = "elife"
    packagepoa_config_file = "packagepoa.cfg"
    packagepoa_config_section = "elife"

    # Decision letter parser
    letterparser_config_file = "letterparser.cfg"
    letterparser_config_section = "elife"

    # PubMed SFTP settings
    PUBMED_SFTP_URI = ""
    PUBMED_SFTP_USERNAME = ""
    PUBMED_SFTP_PASSWORD = ""
    PUBMED_SFTP_CWD = ""

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

    # CLOCKSS FTP settings
    CLOCKSS_FTP_URI = ""
    CLOCKSS_FTP_USERNAME = ""
    CLOCKSS_FTP_PASSWORD = ""
    CLOCKSS_FTP_CWD = ""
    CLOCKSS_EMAIL = "clockss@example.org"

    # OVID FTP settings
    OVID_FTP_URI = ""
    OVID_FTP_USERNAME = ""
    OVID_FTP_PASSWORD = ""
    OVID_FTP_CWD = ""
    OVID_EMAIL = ""

    # Zendy SFTP settings
    ZENDY_SFTP_URI = ""
    ZENDY_SFTP_USERNAME = ""
    ZENDY_SFTP_PASSWORD = ""
    ZENDY_SFTP_CWD = ""
    ZENDY_EMAIL = ""

    # OA Switchboard SFTP settings
    OASWITCHBOARD_SFTP_URI = ""
    OASWITCHBOARD_SFTP_USERNAME = ""
    OASWITCHBOARD_SFTP_PASSWORD = ""
    OASWITCHBOARD_SFTP_CWD = ""
    OASWITCHBOARD_EMAIL = ""

    # Scilit SFTP settings
    SCILIT_SFTP_URI = ""
    SCILIT_SFTP_USERNAME = ""
    SCILIT_SFTP_PASSWORD = ""
    SCILIT_SFTP_CWD = ""
    SCILIT_EMAIL = ""

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
    git_repo_path = "articles/"

    # eLife 2.0 bot lax communication settings
    xml_info_queue = "bot-lax-prod-inc"
    lax_response_queue = "bot-lax-prod-out"

    # videos
    video_url = "https://video.url.here/"

    # PDF cover
    pdf_cover_generator = "http://localhost:8082/personalcover/generate/"
    pdf_cover_landing_page = "http://localhost:8082/personalcover/landing/"

    # IIIF
    path_to_iiif_server = "https://pathto--iiif.elifesciences.org/"
    iiif_resolver = "{article_id}/{article_fig}/full/full/0/default.jpg"

    # Fastly CDNs
    fastly_service_ids = ["3M35rb7puabccOLrFFxy2"]
    fastly_api_key = "fake_fastly_api_key"

    article_path_pattern = "/articles/{id}v{version}"

    # BigQuery settings
    big_query_project_id = ""

    # DOAJ deposit settings
    journal_eissn = ""
    doaj_url_link_pattern = "https://example.org/articles/{article_id}"
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

    # ERA article incoming queue
    era_incoming_queue = "prod-era-incoming-queue"

    # Accepted submission workflow
    accepted_submission_output_bucket = (
        "live-elife-bot-accepted-submission-cleaning-output"
    )
    accepted_submission_sender_email = "sender@example.org"
    accepted_submission_validate_error_recipient_email = ""
    accepted_submission_queue = "cleaning-queue"
    accepted_submission_output_recipient_email = "e@example.org"

    # Glencoe video deposit FTP settings
    GLENCOE_FTP_URI = ""
    GLENCOE_FTP_USERNAME = ""
    GLENCOE_FTP_PASSWORD = ""
    GLENCOE_FTP_CWD = ""

    downstream_recipients_yaml = "downstreamRecipients.yaml"

    publication_email_yaml = "publicationEmail.yaml"

    docmap_url_pattern = (
        "https://example.org/path/get-by-manuscript-id?manuscript_id={article_id}"
    )
    docmap_account_id = "https://sciety.org/groups/elife"
    docmap_index_url = "https://example.org/path/index"

    assessment_terms_yaml = "assessment_terms.yaml"

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

    meca_bucket = "meca_bucket"


def get_settings(ENV="dev"):
    """
    Return the settings class based on the environment type provided,
    by default use the dev environment settings
    """
    return eval(ENV)
