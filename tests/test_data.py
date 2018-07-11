import json
import base64

lax_article_versions_response_data = [
                                        {
                                          "status": "poa",
                                          "version": 1,
                                          "published": "2015-11-26T00:00:00Z",
                                          "versionDate": "2015-11-26T00:00:00Z"
                                        },
                                        {
                                          "status": "poa",
                                          "version": 2,
                                          "published": "2015-11-26T00:00:00Z",
                                          "versionDate": "2015-11-30T00:00:00Z"
                                        },
                                        {
                                          "status": "vor",
                                          "version": 3,
                                          "published": "2015-11-26T00:00:00Z",
                                          "versionDate": "2015-12-29T00:00:00Z"
                                        }
                                      ]

lax_article_by_version_response_data_incomplete = {
                                                      "status": "vor",
                                                      "versionDate": "2016-11-11T17:48:41.715Z",
                                                      "abstract": {
                                                        "content": [
                                                          {
                                                            "text": "Nutritional restriction leads "
                                                                    "to protein translation attenuation that results "
                                                                    "in the storage and",
                                                            "type": "paragraph"
                                                          }
                                                        ],
                                                        "doi": "10.7554/eLife.04132.001"
                                                      },
                                                      "keywords": [
                                                        "protein transport through the secretory pathway",
                                                        "amino-acid starvation",
                                                        "ER exit sites",
                                                        "COPII",
                                                        "liquid droplets",
                                                        "stress granules"
                                                      ]
                                                    }


data_published_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "published",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "publish",
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        }

data_ingested_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "ingested",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "ingest",
            "force": False,
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        }

data_published_website = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "update_date": "2012-12-13T00:00:00Z"
        }

data_error_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "error",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "requested_action": "publish",
            "message": "An error abc has occurred",
            "update_date": "2012-12-13T00:00:00Z"
        }

data_invalid_lax = {
            "run": None,
            "article_id": None,
            "result": "invalid",
            "status": None,
            "version": None,
            "expanded_folder": None,
            "requested_action": "publish",
            "force": False,
            "message": "An error abc has occurred - everything is invalid",
            "update_date": None
        }

silent_ingest_article_zip_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                                  u'event_time': u'2016-07-28T16:14:27.809576Z',
                                  u'event_name': u'ObjectCreated:Put',
                                  u'file_name': u'elife-00353-vor-r1.zip',
                                  u'file_etag': u'e7f639f63171c097d4761e2d2efe8dc4',
                                  u'bucket_name': u'jen-elife-production-final',
                                  u'file_size': 1097506}

ingest_article_zip_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                           u"article_id": u"00353",
                           u"version_reason": "article version reason",
                           u"scheduled_publication_date": "1520585023"}

ingest_article_zip_no_vr_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                                 u"article_id": u"00353"}

initial_article_zip_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                            u'event_time': u'2016-07-28T16:14:27.809576Z',
                            u'event_name': u'ObjectCreated:Put',
                            u'file_name': u'elife-00353-vor-r1.zip',
                            u'file_etag': u'e7f639f63171c097d4761e2d2efe8dc4',
                            u'bucket_name': u'jen-elife-production-final',
                            u'file_size': 1097506}

ingest_digest_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                      u'event_time': u'2018-06-18T16:14:27.809576Z',
                      u'event_name': u'ObjectCreated:Put',
                      u'file_name': u'DIGEST 99999.docx',
                      u'file_etag': u'e7f639f63171c097d4761e2d2efe8dc4',
                      u'bucket_name': u'exp-elife-bot-digests-input',
                      u'file_size': 14086}

queue_worker_rules = {
    'ArticleZip': {
        'bucket_name_pattern': '.*elife-production-final$',
        'file_name_pattern': '.*\.zip',
        'starter_name': 'InitialArticleZip'
        },
    'SilentCorrectionsArticleZip': {
       'bucket_name_pattern': '.*elife-silent-corrections$',
       'file_name_pattern': '.*\.zip',
       'starter_name': 'SilentCorrectionsIngest'
       },
    'DigestInputFile': {
       'bucket_name_pattern': '.*elife-bot-digests-input$',
       'file_name_pattern': '.*\.(docx|zip)',
       'starter_name': 'IngestDigest'
       },
    }

queue_worker_article_zip_data = {u'event_time': u'2016-07-28T16:14:27.809576Z',
                                 u'event_name': u'ObjectCreated:Put',
                                 u'file_name': u'elife-00353-vor-r1.zip',
                                 u'file_etag': u'e7f639f63171c097d4761e2d2efe8dc4',
                                 u'bucket_name': u'jen-elife-production-final',
                                 u'file_size': 1097506}

queue_worker_starter_message = {
    "workflow_name": "InitialArticleZip",
    "workflow_data": {
        "event_time": "2016-07-28T16:14:27.809576Z",
        "event_name": "ObjectCreated:Put",
        "file_name": "elife-00353-vor-r1.zip",
        "file_etag": "e7f639f63171c097d4761e2d2efe8dc4",
        "bucket_name": "jen-elife-production-final",
        "file_size": 1097506
        }
    }

def ApprovePublication_data(update_date="2012-12-13T00:00:00Z"):
        return {
            "article_id": "00353",
            "version": "1",
            "run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
            "publication_data": base64.encodestring(json.dumps(ApprovePublication_publication_data(update_date)))
            }

def ApprovePublication_json_output_return_example(update_date):
            return ApprovePublication_publication_data(update_date)

def ApprovePublication_publication_data(update_date):
            return {
                "workflow_name": "PostPerfectPublication",
                "workflow_data": {
                            "status": "vor",
                            "update_date": update_date,
                            "run": "cf9c7e86-7355-4bb4-b48e-0bc284221251",
                            "expanded_folder": "00353.1/cf9c7e86-7355-4bb4-b48e-0bc284221251",
                            "version": "1",
                            "article_id": "00353"}
                }

glencoe_metadata = \
    {"media2": {
        "source_href": "http://static-movie-usa.glencoesoftware.com/source/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.mov", "doi": "10.7554/eLife.12620.008",
        "flv_href": "http://static-movie-usa.glencoesoftware.com/flv/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.flv",
        "uuid": "674a799d-20f8-40c2-99b2-b9bd18fe6b7b",
        "title": "",
        "video_id": "media2",
        "solo_href": "http://movie-usa.glencoesoftware.com/video/10.7554/eLife.12620/media2",
        "height": 512,
        "ogv_href": "http://static-movie-usa.glencoesoftware.com/ogv/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.ogv",
        "width": 512,
        "href": "elife-12620-media2.mov",
        "webm_href": "http://static-movie-usa.glencoesoftware.com/webm/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.webm",
        "jpg_href": "http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.jpg",
        "duration": 43.159999999999997,
        "mp4_href": "http://static-movie-usa.glencoesoftware.com/mp4/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media2.mp4",
        "legend": "<div class=\"caption\"><h3 class=\"title\">Effects of a highly-focused laser spot on directional motility in <i>Synechocystis.<\/i><\/h3><p>Cells are imaged by fluorescence from the photosynthetic pigments, and are moving towards an oblique LED light at the bottom of the frame: note the focused light spot at the rear edge of each cell. The superimposed red spot indicates the position of the laser, and time in min is shown at the top left.&#160;LED, light emitting diode.<\/p><p><b>DOI:<\/b> <a href=\"10.7554/eLife.12620.008\">http://dx.doi.org/10.7554/eLife.12620.008<\/a><\/p><\/div>", "size": 2578518},
     "media1": {
         "source_href": "http://static-movie-usa.glencoesoftware.com/source/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.mp4",
         "doi": "10.7554/eLife.12620.004",
         "flv_href": "http://static-movie-usa.glencoesoftware.com/flv/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.flv",
         "uuid": "e1f617d7-a3d7-45ec-8fcc-6b66f8f26505",
         "title": "",
         "video_id": "media1",
         "solo_href": "http://movie-usa.glencoesoftware.com/video/10.7554/eLife.12620/media1",
         "height": 720,
         "ogv_href": "http://static-movie-usa.glencoesoftware.com/ogv/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.ogv",
         "width": 1280, "href": "elife-12620-media1.mp4",
         "webm_href": "http://static-movie-usa.glencoesoftware.com/webm/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.webm",
         "jpg_href": "http://static-movie-usa.glencoesoftware.com/jpg/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.jpg",
         "duration": 89.400000000000006, "mp4_href": "http://static-movie-usa.glencoesoftware.com/mp4/10.7554/114/1245b554bd5cbda4fa4beeba806e659f0624128e/elife-12620-media1.mp4",
         "legend": "<div class=\"caption\"><h3 class=\"title\">Motility of <i>Synechocystis<\/i> cells under different illumination regimes.<\/h3><p>The video gives a schematic overview of the experimental set-up, followed by movement of cells in a projected light gradient, and with oblique illumination from two orthogonal directions, and then from both directions simultaneously. In each case, the raw video data is followed by the same movie clip with the tracks of cells superimposed. Time in minutes is indicated.<\/p><p><b>DOI:<\/b> <a href=\"10.7554/eLife.12620.004\">http://dx.doi.org/10.7554/eLife.12620.004<\/a><\/p><\/div>",
         "size": 21300934}}
