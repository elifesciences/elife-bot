import json
import os
from elifearticle import parse
import provider.article as articlelib
from provider.execution_context import get_session
from provider import software_heritage, utils
from provider.storage_provider import storage_context
from activity.objects import Activity


README_FILENAME = "README.md"


class activity_GenerateSWHReadme(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_GenerateSWHReadme, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "GenerateSWHReadme"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Generate readme file for inclusion in a Software Heritage deposit"
        )
        self.logger = logger

        # Local directory settings
        self.directories = {
            "TMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        run = data["run"]
        session = get_session(self.settings, data, run)
        article_id = session.get_value("article_id")
        version = session.get_value("version")
        input_file = session.get_value("input_file")
        bucket_resource = session.get_value("bucket_resource")
        create_origin_url = session.get_value("create_origin_url")
        self.logger.info(
            (
                "%s activity session data: article_id: %s, version: %s, input_file: %s, "
                "bucket_resource: %s, create_origin_url: %s"
            )
            % (
                self.name,
                article_id,
                version,
                input_file,
                bucket_resource,
                create_origin_url,
            )
        )

        storage = storage_context(self.settings)

        # download article XML file
        try:
            bot_article = articlelib.article(self.settings)
            article_xml_filename = bot_article.download_article_xml_from_s3(
                self.get_tmp_dir(), utils.pad_msid(article_id)
            )
            self.logger.info(
                "Downloaded article XML for %s to %s"
                % (article_id, article_xml_filename)
            )
        except Exception:
            self.logger.exception(
                "Exception raised downloading article XML for %s" % article_id
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # parse XML into article object
        try:
            article, error_count = parse.build_article_from_xml(
                os.path.join(self.get_tmp_dir(), article_xml_filename), detail="full"
            )
            self.logger.info(
                "Parsed article doi %s, error_count: %s" % (article.doi, error_count)
            )
        except Exception:
            self.logger.exception(
                "Exception raised parsing article XML for %s" % article_xml_filename
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # generate readme file
        try:
            readme_keywords = {
                "article_title": article.title,
                "doi": utils.get_doi_url(article.doi),
                "article_id": utils.pad_msid(article_id),
                "create_origin_url": create_origin_url,
                "content_license": article.license.href,
            }
            readme_string = software_heritage.readme(readme_keywords)
            readme_string = bytes(readme_string, "utf8")
            self.logger.info("Readme generated for article doi %s" % article.doi)
        except Exception:
            self.logger.exception(
                "Exception raised creating readme for article doi %s" % article.doi
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        self.logger.info(
            "Readme string for article doi %s: %s" % (article.doi, readme_string)
        )

        # upload XML metadata file to bucket
        try:
            readme_filename = README_FILENAME
            resource_path = "/".join(
                [
                    software_heritage.BUCKET_FOLDER,
                    run,
                    readme_filename,
                ]
            )
            resource_dest = "%s://%s/%s" % (
                self.settings.storage_provider,
                self.settings.bot_bucket,
                resource_path,
            )
            storage.set_resource_from_string(resource_dest, readme_string)
            self.logger.info(
                "Uploaded readme for article %s to %s" % (article.doi, resource_dest)
            )
        except Exception:
            self.logger.exception(
                "Exception raised uploading readme to bucket for article doi %s"
                % article.doi
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # save S3 location in session
        session.store_value("bucket_readme_resource", resource_path)

        # clean temporary directory
        self.clean_tmp_dir()

        # return success
        return self.ACTIVITY_SUCCESS
