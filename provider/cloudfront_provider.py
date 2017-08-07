import boto.cloudfront as cloudfront


def create_invalidation(article, distribution_id):
    inval_req = cloudfront.create_invalidation_request(distribution_id, "/articles/" + article + "/*")
    assert isinstance(inval_req, cloudfront.invalidation.InvalidationBatch), \
        "Invalidation request did not return expected object."
