import activity
import json
from provider.execution_context import Session
from provider.storage_provider import StorageContext
import provider.glencoe_check as glencoe_check
import os
import requests


"""
activity_CopyGlencoeStillImages.py activity
"""


class ValidationException(RuntimeError):
    pass

class activity_CopyGlencoeStillImages(activity.activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        activity.activity.__init__(self, settings, logger, conn, token, activity_task)

        self.name = "CopyGlencoeStillImages"
        self.pretty_name = "Copy Glencoe Still Images"
        self.version = "1"
        self.default_task_heartbeat_timeout = 30
        self.default_task_schedule_to_close_timeout = 60 * 5
        self.default_task_schedule_to_start_timeout = 30
        self.default_task_start_to_close_timeout = 60 * 5
        self.description = "Copies the Glencoe video still images to the CDN bucket"
        self.logger = logger

    def do_activity(self, data=None):

        if self.logger:
            self.logger.info('data: %s' % json.dumps(data, sort_keys=True, indent=4))

        try:
            run = data['run']
            session = Session(self.settings)
            article_id = session.get_value(run, 'article_id')
            version = session.get_value(run, 'version')
        except Exception as e:
            self.logger.exception("Error starting Copy Glencoe Still Images activity")
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "start",
                                "Starting check/copy of Glencoe video still images " + article_id)
        try:
            padded_article_id = glencoe_check.check_msid(article_id)
            metadata = glencoe_check.metadata(padded_article_id, self.settings)
            jpgs = glencoe_check.jpg_href_values(metadata)
            self.logger.info("jpgs from glencoe metadata " + str(jpgs))
            bad_files = []
            if len(jpgs) > 0:
                jpg_filenames = self.store_jpgs(jpgs, article_id)

                bad_files = self.validate_jpgs_against_cdn(self.list_files_from_cdn(article_id), jpg_filenames,
                                                           article_id)
            if len(bad_files) > 0:
                self.logger.error("Videos do not have a glencoe ")
                bad_files.sort()
                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                        "Not all still images .jpg have a video with the same name " +
                                        "missing videos file names: " + str(bad_files) +
                                        " Please check them against CDN files.")
                return activity.activity.ACTIVITY_PERMANENT_FAILURE

            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                    "Finished Copying Glencoe still images to CDN. "
                                    "Article: " + article_id)

            return activity.activity.ACTIVITY_SUCCESS
        except AssertionError as e:
            self.logger.info(str(e.message))
            first_chars_error = str(e.message[:21])
            if first_chars_error == "article has no videos":
                self.logger.error("Glencoe returned 404, therefore article %s does not have videos", article_id)
                self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "end",
                                        "Glencoe returned 404, therefore article has no videos")
                return activity.activity.ACTIVITY_SUCCESS

            self.logger.exception("Error when checking/copying Glencoe still images.")
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "An error occurred when checking/copying Glencoe still images. Article " +
                                    article_id + '; message: ' + str(e.message))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE

        except Exception as e:
            self.logger.exception("Error when checking/copying Glencoe still images.")
            self.emit_monitor_event(self.settings, article_id, version, run, self.pretty_name, "error",
                                    "An error occurred when checking/copying Glencoe still images. Article " +
                                    article_id + '; message: ' + str(e))
            return activity.activity.ACTIVITY_PERMANENT_FAILURE


    def store_jpgs(self, jpgs, article_id):
        jpg_filenames = []
        for jpg in jpgs:
                    jpg_filename = self.store_file(jpg, article_id)
                    jpg_filenames.append(jpg_filename)
        return jpg_filenames

    def s3_resource(self, path, article_id):
        filename = os.path.split(path)[1]
        filename = glencoe_check.extend_article_for_end2end(filename, article_id)
        return self.settings.storage_provider + "://" + \
               self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket + "/" + \
               article_id + "/" + filename

    def store_file(self, path, article_id):
        storage_context = StorageContext(self.settings)
        r = requests.get(path)
        if r.status_code == 200:
            resource = self.s3_resource(path, article_id)
            self.logger.info("S3 resource: " + resource)
            jpg_filename = os.path.split(path)[1]
            storage_context.set_resource_from_string(resource, r.content,
                                                     content_type=r.headers['content-type'])
            return jpg_filename


    def list_files_from_cdn(self, article_id):
        storage_context = StorageContext(self.settings)
        article_path_in_cdn = self.settings.storage_provider + "://" + \
                              self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket + "/" + \
                              article_id
        return storage_context.list_resources(article_path_in_cdn)

    def validate_jpgs_against_cdn(self, files_in_cdn, jpgs, article_id):
        jpgs_rep_no_extension = list(map(lambda filename: os.path.splitext(filename)[0], jpgs))
        self.logger.info("jpgs_rep_no_extension " + str(jpgs_rep_no_extension))
        files_in_cdn_no_extension = list(map(lambda filename: os.path.splitext(filename)[0], files_in_cdn))
        self.logger.info("files_in_cdn_no_extention " + str(files_in_cdn_no_extension))
        # files_in_cdn_article_padded = list(map(lambda filename: glencoe_check.pad_article_for_end2end(filename, article_id),
        #                                   files_in_cdn_no_extention))
        # self.logger.info("files_in_cdn_article_padded " + str(files_in_cdn_article_padded))
        jpgs_without_video = []
        for file_no_ext in jpgs_rep_no_extension:
            if len(list(filter(lambda filename: filename == file_no_ext, files_in_cdn_no_extension))) != 2:
                jpgs_without_video.append(file_no_ext)

        self.logger.info("jpgs_without_video " + str(jpgs_without_video))
        return jpgs_without_video

    # def validate_cdn(self, files_in_cdn):
    #     videos = list(filter(article_structure.is_media_file, files_in_cdn))
    #     videos_as_jpg = list(map(lambda filename: os.path.splitext(filename[0]+'.jpg'), videos))
    #     do_videos_match_jpgs = (len(set(videos_as_jpg) & set(files_in_cdn)) == len(videos))
    #     return do_videos_match_jpgs, files_in_cdn, videos






