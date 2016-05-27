import unittest
from end2end import generator
from end2end import input
from end2end import checks

class TestPublishing(unittest.TestCase):
    def test_uploaded_article_gets_transformed_into_eif(self):
        article = generator.article_zip()
        input.production_bucket(article)
        checks.eif(article.doi())
        pass

