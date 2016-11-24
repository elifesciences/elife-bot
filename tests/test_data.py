
lax_article_versions_response_data = [
                                        {
                                          "status": "poa",
                                          "version": 1,
                                          "published": "2015-11-26T00:00:00Z"
                                        },
                                        {
                                          "status": "poa",
                                          "version": 2,
                                          "published": "2015-11-30T00:00:00Z"
                                        },
                                        {
                                          "status": "vor",
                                          "version": 3,
                                          "published": "2015-12-29T00:00:00Z"
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
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
            "requested_action": "publish",
            "message": None,
            "update_date": "2012-12-13T00:00:00Z"
        }

data_published_website = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
            "update_date": "2012-12-13T00:00:00Z"
        }

data_error_lax = {
            "run": "74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "article_id": "00353",
            "result": "error",
            "status": "vor",
            "version": "1",
            "expanded_folder": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff",
            "eif_location": "00353.1/74e22d8f-6b5d-4fb7-b5bf-179c1aaa7cff/elife-00353-v1.json",
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
            "eif_location": None,
            "requested_action": "publish",
            "message": "An error abc has occurred - everything is invalid",
            "update_date": None
        }

ingest_article_zip_data = {u'run': u'1ee54f9a-cb28-4c8e-8232-4b317cf4beda',
                           u'event_time': u'2016-07-28T16:14:27.809576Z',
                           u'event_name': u'ObjectCreated:Put',
                           u'file_name': u'elife-00353-vor-r1.zip',
                           u'file_etag': u'e7f639f63171c097d4761e2d2efe8dc4',
                           u'bucket_name': u'jen-elife-production-final',
                           u'file_size': 1097506}