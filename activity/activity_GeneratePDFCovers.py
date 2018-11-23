import provider.article as articlelib
from .activity import Activity

"""
activity_GeneratePDFCovers.py activity
"""

class activity_GeneratePDFCovers(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_GeneratePDFCovers, self).__init__(
            settings, logger, conn, token, activity_task)

        self.name = "GeneratePDFCovers"
        self.pretty_name = "Generate PDF Covers"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Generates PDF covers for article if not already done"
        self.logger = logger

    def do_activity(self, data):
        try:
            article_id = data['article_id']
            version = data['version']
            run = data['run']
        except Exception as e:
            self.logger.error("Error retrieving basic article data. Data: %s, Exception: %s" % (str(data), str(e)))
            return self.ACTIVITY_PERMANENT_FAILURE

        try:

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start", "Starting check for generation of pdf cover.")

            article = articlelib.article()

            if not (hasattr(self.settings, "pdf_cover_generator")) or \
                    (hasattr(self.settings, "pdf_cover_generator") and self.settings.pdf_cover_generator == None) or \
                    (hasattr(self.settings, "pdf_cover_generator") and len(self.settings.pdf_cover_generator) < 1):

                self.emit_monitor_event(self.settings, article_id, version, run,
                                        self.pretty_name, "start", "pdf_cover_generator variable is missing from "
                                                          "settings file. PDF not generated but flag is set "
                                                          "for the activity to succeed.")
                return self.ACTIVITY_SUCCESS

            pdf_cover = article.get_pdf_cover_link(self.settings.pdf_cover_generator, article_id, self.logger)

            assert "a4" in pdf_cover and "letter" in pdf_cover and len(pdf_cover["a4"]) > 1 \
                   and len(pdf_cover["letter"]) > 1, "Unexpected result from pdf covers API."

            dashboard_message = ("Finished check for generation of pdf cover. S3 url for a4: %s; "
                                 "S3 url for letter %s.") % (pdf_cover["a4"], pdf_cover["letter"])
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "end", dashboard_message)
            return self.ACTIVITY_SUCCESS

        except AssertionError as err:
            error_message = str(err)
            self.logger.error(error_message)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error", error_message)
            return self.ACTIVITY_PERMANENT_FAILURE

        except Exception as e:
            error_message = str(e)
            self.logger.error(error_message)
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error", error_message)
            return self.ACTIVITY_PERMANENT_FAILURE
