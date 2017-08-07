import boto.cloudfront as cloudfront


def create_invalidation(article, settings):
    inval_req = cloudfront.create_invalidation_request(settings.cloudfront_distribution_id_cdn,
                                                 "/articles/" + article + "/*")
    assert isinstance(inval_req, cloudfront.invalidation.InvalidationBatch), \
        "Invalidation request did not return expected object."
