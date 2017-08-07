import boto.cloudfront as cloudfront


def create_invalidation(article, settings):
    cloudfront.create_invalidation_request(settings.cloudfront_distribution_id_cdn,
                                           "/articles/" + article + "/*")