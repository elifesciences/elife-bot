from boto.cloudfront import CloudFrontConnection


def create_invalidation(article, settings):
    cloudfront = CloudFrontConnection((settings.aws_access_key_id, settings.aws_secret_access_key))
    inval_req = cloudfront.create_invalidation_request(settings.cloudfront_distribution_id_cdn,
                                                       "/articles/" + article + "/*")
    assert isinstance(inval_req, cloudfront.invalidation.InvalidationBatch), \
        "Invalidation request did not return expected object."
