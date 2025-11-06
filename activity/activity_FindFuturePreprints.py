import json, os
from provider import bigquery, outbox_provider, preprint, utils
from activity.objects import Activity
from activity.activity_DepositCrossrefPendingPublication import (
    PLACEHOLDER_ARTICLE_TITLE,
)


# number of days into the future to look for future preprint data in BigQuery
QUERY_DAY_INTERVAL = 7


class activity_FindFuturePreprints(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_FindFuturePreprints, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "FindFuturePreprints"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = (
            "Find preprint versions with a future publication date and"
            " queue a workflow for each"
        )

        # For copying to S3 bucket outbox
        self.crossref_outbox_folder = outbox_provider.outbox_folder(
            self.s3_bucket_folder("DepositCrossrefPendingPublication")
        )

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

    def do_activity(self, data=None):
        self.logger.info("data: %s" % json.dumps(data, sort_keys=True, indent=4))

        self.make_activity_directories()

        # query to find future preprints
        preprint_list = get_future_preprint_data(self.settings, self.name, self.logger)

        self.logger.info(
            "%s, found %s future preprints" % (self.name, len(preprint_list))
        )

        for preprint_object in preprint_list:
            article_id = utils.msid_from_doi(preprint_object.doi)
            version_doi = ".".join([preprint_object.doi, str(preprint_object.version)])

            try:
                xml_string = generate_preprint_xml_string(
                    article_id,
                    preprint_object.doi,
                    version_doi,
                    self.settings,
                    self.name,
                    self.logger,
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception raised generating an XML string for version_doi %s: %s"
                    % (self.name, version_doi, str(exception))
                )
                continue

            # generate preprint XML stub and add to S3 outbox folder
            xml_file_name = preprint.xml_filename(
                utils.msid_from_doi(preprint_object.doi),
                self.settings,
                preprint_object.version,
            )
            self.logger.info(
                "%s, generating XML file %s for version_doi %s"
                % (self.name, xml_file_name, version_doi)
            )

            # write XML to file
            xml_file_path = os.path.join(
                self.directories.get("TEMP_DIR"), xml_file_name
            )
            with open(xml_file_path, "wb") as open_file:
                open_file.write(xml_string)

            # upload to the outbox folder
            outbox_provider.upload_files_to_s3_folder(
                self.settings,
                self.settings.poa_packaging_bucket,
                self.crossref_outbox_folder,
                [xml_file_path],
            )

            self.logger.info(
                ("%s, uploaded %s to S3 bucket %s, folder %s")
                % (
                    self.name,
                    xml_file_path,
                    self.settings.poa_packaging_bucket,
                    self.crossref_outbox_folder,
                )
            )

        return self.ACTIVITY_SUCCESS


def generate_preprint_xml_string(
    article_id, doi, version_doi, settings, caller_name, logger
):
    "generate an XML string for the preprint version"
    title = PLACEHOLDER_ARTICLE_TITLE
    accepted_date_struct = utils.get_current_datetime().timetuple()
    logger.info(
        "%s, generating article object for version_doi %s" % (caller_name, version_doi)
    )
    article_object = preprint.build_simple_article(
        article_id,
        doi,
        title,
        version_doi,
        accepted_date_struct,
    )
    return preprint.preprint_xml(article_object, settings)


def get_future_preprint_data(settings, caller_name, logger):
    "from BigQuery get a list of preprints having a future publication date"
    bigquery_client = bigquery.get_client(settings, logger)
    query_result = None
    try:
        query_result = bigquery.future_preprint_article_result(
            bigquery_client, QUERY_DAY_INTERVAL
        )
    except Exception as exception:
        logger.exception(
            ("%s, exception getting a list of future preprints" " from BigQuery: %s")
            % (caller_name, str(exception))
        )
    if query_result:
        return bigquery.preprint_objects(query_result)
    return None
