from datetime import datetime
import json
import os
from provider.execution_context import get_session
from provider import (
    cleaner,
    docmap_provider,
    utils,
)
from activity.objects import Activity


# DOI prefix for generating DOI value
DOI_PREFIX = "10.7554/eLife."


class activity_MecaDetails(Activity):
    def __init__(self, settings, logger, client=None, token=None, activity_task=None):
        super(activity_MecaDetails, self).__init__(
            settings, logger, client, token, activity_task
        )

        self.name = "MecaDetails"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Collect details about a MECA file to be ingested"

        # Local directory settings
        self.directories = {
            "TEMP_DIR": os.path.join(self.get_tmp_dir(), "tmp_dir"),
            "INPUT_DIR": os.path.join(self.get_tmp_dir(), "input_dir"),
        }

        # Track the success of some steps
        self.statuses = {"docmap_string": None}

    def do_activity(self, data=None):
        """
        Activity, do the work
        """
        self.logger.info(
            "%s data: %s" % (self.name, json.dumps(data, sort_keys=True, indent=4))
        )

        self.make_activity_directories()

        # start session
        run = data["run"]
        session = get_session(self.settings, data, run)
        session.store_value("run", run)
        session.store_value("run_type", data.get("run_type"))

        if (
            data.get("run_type") == "silent-correction"
            and data.get("bucket_name")
            and data.get("file_name")
        ):
            # get computer_file_url, article_id, and version from the S3 notification data
            computer_file_url = "%s://%s" % (
                self.settings.storage_provider,
                "/".join([data.get("bucket_name"), data.get("file_name")]),
            )
            filename_last_element = data.get("file_name").rsplit("/", 1)[-1]
            article_id, version = meca_file_parts(filename_last_element)
            version_doi = "%s%s.%s" % (DOI_PREFIX, utils.pad_msid(article_id), version)
        else:
            # store details in session
            article_id = data.get("article_id")
            version = data.get("version")
            computer_file_url = None

        # store details in session
        session.store_value("article_id", article_id)
        session.store_value("version", str(version))

        # get docmap as a string
        self.logger.info(
            "%s, getting docmap_string for article_id %s" % (self.name, article_id)
        )
        try:
            docmap_string = cleaner.get_docmap_string_with_retry(
                self.settings, article_id, self.name, self.logger
            )
            self.statuses["docmap_string"] = True
            # save the docmap_string to the session
            session.store_value(
                "docmap_datetime_string",
                datetime.strftime(utils.get_current_datetime(), utils.DATE_TIME_FORMAT),
            )
            session.store_value("docmap_string", docmap_string.decode("utf-8"))
        except Exception as exception:
            self.logger.exception(
                "%s, exception getting a docmap for article_id %s: %s"
                % (self.name, article_id, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        # parse docmap JSON
        self.logger.info(
            "%s, parsing docmap_string for article_id %s" % (self.name, article_id)
        )
        try:
            docmap_json = json.loads(docmap_string)
        except Exception as exception:
            self.logger.exception(
                "%s, exception parsing docmap_string for article_id %s: %s"
                % (self.name, article_id, str(exception))
            )
            return self.ACTIVITY_PERMANENT_FAILURE

        version_doi = "%s%s.%s" % (DOI_PREFIX, article_id, version)
        session.store_value("version_doi", version_doi)

        self.logger.info(
            "%s, version_doi %s for article_id %s, version %s"
            % (self.name, version_doi, article_id, version)
        )

        if not computer_file_url:
            # get a version DOI step map from the docmap
            try:
                steps = steps_by_version_doi(
                    docmap_json, version_doi, self.name, self.logger
                )
            except Exception as exception:
                self.logger.exception(
                    "%s, exception in steps_by_version_doi for version DOI %s: %s"
                    % (self.name, version_doi, str(exception))
                )
                return self.ACTIVITY_PERMANENT_FAILURE
            if not steps:
                self.logger.info(
                    "%s, found no docmap steps for version DOI %s"
                    % (self.name, version_doi)
                )
                return self.ACTIVITY_PERMANENT_FAILURE

            # get computer-file url from the docmap
            computer_file_url = self.get_computer_file_url(steps, version_doi)

        if not computer_file_url:
            self.logger.info(
                "%s, computer_file_url not found in computer_file for version DOI %s"
                % (self.name, version_doi)
            )
            return self.ACTIVITY_PERMANENT_FAILURE
        self.logger.info(
            "%s, computer_file_url %s for version_doi %s"
            % (self.name, computer_file_url, version_doi)
        )

        session.store_value("computer_file_url", computer_file_url)

        self.clean_tmp_dir()

        self.logger.info(
            "%s, statuses for version DOI %s: %s"
            % (self.name, version_doi, self.statuses)
        )

        return self.ACTIVITY_SUCCESS

    def get_computer_file_url(self, steps, version_doi):
        "return computer_file_url from the docmap for the original input MECA"
        return docmap_provider.input_computer_file_url_from_steps(
            steps, version_doi, self.name, self.logger
        )


def meca_file_parts(file_name):
    "get data from MECA file name"
    parts = file_name.split("-")
    article_id = int(parts[0])
    version = parts[1].replace("v", "")
    return article_id, version


def steps_by_version_doi(docmap_json, version_doi, caller_name, logger):
    "get steps from the docmap for the version_doi"
    logger.info(
        "%s, getting a step map for version DOI %s" % (caller_name, version_doi)
    )
    try:
        step_map = docmap_provider.version_doi_step_map(docmap_json)
    except Exception as exception:
        logger.exception(
            "%s, exception getting a step map for version DOI %s: %s"
            % (caller_name, version_doi, str(exception))
        )
        raise

    return step_map.get(version_doi)
