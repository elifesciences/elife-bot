import activity
import provider.article as articlelib

"""
activity_GeneratePDFCovers.py activity
"""

class activity_GeneratePDFCovers(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

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
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        try:

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start", "Starting check for generation of pdf cover.")

            article = articlelib.article()
            pdf_cover_a4 = article.get_pdf_cover_link(self.logger, self.settings, article_id, "a4")
            pdf_cover_letter = article.get_pdf_cover_link(self.logger, self.settings, article_id, "letter")

            assert len(pdf_cover_a4) > 1 and len(pdf_cover_letter) > 1, "Unexpected result from pdf covers API."

            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "start", "Finished check for generation of pdf cover.")
            return activity.activity.ACTIVITY_SUCCESS

        except AssertionError as err:
            self.logger.error(str(err))
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error", err)
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        except Exception as e:
            self.logger.error(str(e))
            self.emit_monitor_event(self.settings, article_id, version, run,
                                    self.pretty_name, "error", str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE




