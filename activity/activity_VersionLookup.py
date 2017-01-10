
import activity
from S3utility.s3_notification_info import S3NotificationInfo
from provider.execution_context import Session
from provider.article_structure import ArticleInfo
import provider.lax_provider

lookup_functions = { "article_next_version": provider.lax_provider.article_next_version,
                     "article_highest_version": provider.lax_provider.article_highest_version }

class activity_VersionLookup(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "VersionLookup"
        self.pretty_name = "Version Lookup"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Looks up version on Lax endpoints and stores version in session"
        self.logger = logger

    def do_activity(self, data=None):

        info = S3NotificationInfo.from_dict(data)
        filename = info.file_name[info.file_name.rfind('/')+1:]
        session = Session(self.settings)
        session.store_value(data['run'], 'filename_last_element', filename)

        article_structure = ArticleInfo(filename)

        if article_structure.article_id is None:
            self.logger.error("Name '%s' did not match expected pattern for article id" % filename)
            raise RuntimeError("article_structure.article_id is None. File pattern problem.")

        try:

            version = self.get_version(self.settings, article_structure, data['version_lookup_function'])
            session.store_value(data['run'], 'version', version)
            article_id = article_structure.article_id
            session.store_value(data['run'], 'article_id', article_id)

            self.emit_monitor_event(self.settings, article_id, version, data['run'],
                                    self.pretty_name, "start",
                                    " ".join(("Version Lookup for article", article_id, "version:", version)))

            self.set_monitor_property(self.settings, article_id, "article-id", article_id, "text")
            self.set_monitor_property(self.settings, article_id, "publication-status", "publication in progress",
                                      "text",
                                      version=version)

            self.emit_monitor_event(self.settings, article_structure.article_id, version, data['run'],
                                    self.pretty_name, "end",
                                    " ".join(("Finished Version Lookup for article", article_structure.article_id,
                                              "version:", version)))
            return activity.activity.ACTIVITY_SUCCESS

        except Exception:
            self.logger.exception("Exception when trying to Lookup Version")
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

    def get_version(self, settings, article_structure, lookup_function):
        try:
            version = article_structure.get_version_from_zip_filename()
            if version is None:
                return str(self.execute_function(lookup_functions[lookup_function], article_structure.article_id, settings))
            return version
        except Exception:
            self.logger.exception("Exception on function `get_version`")
            raise

    def execute_function(self, the_function, arg1, arg2):
        return the_function(arg1, arg2)
