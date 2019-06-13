from activity.objects import Activity
import json
import time
from provider.execution_context import get_session
from provider.storage_provider import storage_context
from provider.article_processing import download_jats
import provider.glencoe_check as glencoe_check
import os
import requests


"""
activity_CopyGlencoeStillImages.py activity
"""


class ValidationException(RuntimeError):
    pass

class activity_CopyGlencoeStillImages(Activity):
    def __init__(self, settings, logger, conn=None, token=None, activity_task=None):
        super(activity_CopyGlencoeStillImages, self).__init__(
            settings, logger, conn, token, activity_task)

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
            if 'standalone' in data and data['standalone']:
                article_id = data['article_id']
                poa = data['standalone_is_poa']
                (start_msg, end_msg, result) = self.get_events(article_id, poa, version=None, run=None)
                self.logger.info(end_msg[6])
                return result

            run = data['run']
            session = get_session(self.settings, data, run)
            article_id = session.get_value('article_id')
            version = session.get_value('version')
            file_name = session.get_value('file_name')
            expanded_folder = session.get_value('expanded_folder')
            poa = False
            if "poa" in file_name:
                poa = True
            # check XML for if it has videos
            jats_file = download_jats(
                self.settings, expanded_folder, self.get_tmp_dir(), self.logger)
            with open(jats_file, 'r') as open_file:
                has_videos = glencoe_check.has_videos(open_file.read())
            # start the image download events
            (start_msg, end_msg, success) = self.get_events(article_id, poa, version, run, has_videos)
            self.emit_monitor_event(*start_msg)
            self.emit_monitor_event(*end_msg)
            return success
        except Exception as e:
            self.logger.exception("Error starting Copy Glencoe Still Images activity")
            return self.ACTIVITY_PERMANENT_FAILURE

    def get_events(self, article_id, poa, version=None, run=None, has_videos=None):

        start_event = [self.settings, article_id, version, run, self.pretty_name, "start",
                       "Starting check/copy of Glencoe video still images " + article_id]
        try:
            if poa:

                end_event = [self.settings, article_id, version, run, self.pretty_name, "end",
                             "Article is POA, no need for video check yet. " + article_id]

                return start_event, end_event, self.ACTIVITY_SUCCESS
            glencoe_article_id = glencoe_check.check_msid(article_id)
            metadata = glencoe_check.metadata(glencoe_article_id, self.settings)
            glencoe_jpgs = glencoe_check.jpg_href_values(metadata)
            self.logger.info("glencoe_jpgs from glencoe metadata " + str(glencoe_jpgs))
            bad_files = []
            if len(glencoe_jpgs) > 0:
                cdn_still_jpgs = self.store_jpgs(glencoe_jpgs, article_id)

                bad_files = self.validate_jpgs_against_cdn(self.list_files_from_cdn(article_id),
                                                           cdn_still_jpgs,
                                                           article_id)

            dashboard_message = ("Finished Copying Glencoe still images to CDN: %s" + \
                                "Article: %s") % \
                                (cdn_still_jpgs, article_id)
            self.logger.info(dashboard_message)

            end_event = [self.settings, article_id, version, run, self.pretty_name, "end",
                         dashboard_message]
            return start_event, end_event, self.ACTIVITY_SUCCESS
        except AssertionError as e:
            self.logger.info(str(e))
            first_chars_error = str(e)[:21]
            if first_chars_error == "article has no videos":
                if has_videos:
                    # article has videos but Glencoe 404, wait and then retry again
                    self.logger.info(e)
                    end_event = [self.settings, article_id, version, run, self.pretty_name, "error",
                                "Glencoe video is not available for article " + article_id + 
                                '; message: ' + str(e)]
                    time.sleep(60)
                    return start_event, end_event, self.ACTIVITY_TEMPORARY_FAILURE
                else:
                    self.logger.info("Glencoe returned 404, therefore article %s does not have videos", article_id)
                    end_event = [self.settings, article_id, version, run, self.pretty_name, "end",
                                "Glencoe returned 404, therefore article has no videos"]
                    return start_event, end_event, self.ACTIVITY_SUCCESS

            self.logger.exception("Error when checking/copying Glencoe still images.")
            end_event = [self.settings, article_id, version, run, self.pretty_name, "error",
                         "An error occurred when checking/copying Glencoe still images. Article " +
                         article_id + '; message: ' + str(e)]
            return start_event, end_event, self.ACTIVITY_PERMANENT_FAILURE

        except Exception as e:
            self.logger.exception("Error when checking/copying Glencoe still images.")
            end_event = [self.settings, article_id, version, run, self.pretty_name, "error",
                         "An error occurred when checking/copying Glencoe still images. Article " +
                         article_id + '; message: ' + str(e)]
            return start_event, end_event, self.ACTIVITY_PERMANENT_FAILURE


    def store_jpgs(self, glencoe_jpgs, article_id):
        cdn_still_jpgs = []
        for jpg in glencoe_jpgs:
            jpg_filename = self.store_file(jpg, article_id)
            cdn_still_jpgs.append(jpg_filename)
        return cdn_still_jpgs

    def s3_resources(self, path, article_id):
        filename = os.path.split(path)[1]
        filename = glencoe_check.force_article_id(filename, article_id)
        cdn = self.settings.storage_provider + "://" + \
               self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket + "/" + \
               article_id + "/" + filename
        return cdn

    def store_file(self, path, article_id):
        storage = storage_context(self.settings)
        r = requests.get(path)
        if r.status_code == 200:
            resource = self.s3_resources(path, article_id)
            self.logger.info("S3 resource: " + resource)
            jpg_filename = os.path.split(resource)[-1]
            storage.set_resource_from_string(
                resource,
                r.content,
                content_type=r.headers['content-type']
            )
            return jpg_filename
        else:
            raise RuntimeError("Glencoe returned a %s status code for %s" % (r.status_code, path))


    def list_files_from_cdn(self, article_id):
        storage = storage_context(self.settings)
        article_path_in_cdn = self.settings.storage_provider + "://" + \
                              self.settings.publishing_buckets_prefix + self.settings.ppp_cdn_bucket + "/" + \
                              article_id
        return storage.list_resources(article_path_in_cdn)

    def validate_jpgs_against_cdn(self, cdn_all_files, cdn_still_jpgs, article_id):
        """checks that for each element of cdn_still_jpgs there are two files in the CDN.

        They are supposed to be a video and its still image"""
        cdn_still_jpgs_no_extension = self._remove_extension(cdn_still_jpgs)
        self.logger.info("cdn_still_jpgs_no_extension " + str(cdn_still_jpgs_no_extension))
        cdn_all_files_no_extension = self._remove_extension(cdn_all_files)
        self.logger.info("files_in_cdn_no_extention " + str(cdn_all_files_no_extension))
        cdn_still_jpgs_without_video = []
        for still in cdn_still_jpgs_no_extension:
            if len(list(filter(lambda filename: filename == still, cdn_all_files_no_extension))) != 2:
                cdn_still_jpgs_without_video.append(still)

        self.logger.info("cdn_still_jpgs_without_video " + str(cdn_still_jpgs_without_video))
        return cdn_still_jpgs_without_video

    def _remove_extension(self, filenames):
        return list(map(lambda filename: os.path.splitext(filename)[0], filenames))
