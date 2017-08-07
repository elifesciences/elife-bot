import boto.cloudfront as cloudfront
import settings


def create_invalidation(article):
    cloudfront.create_invalidation_request(settings.cloudfront_distribution_id_cdn,
                                           "/articles/" + article + "/*")