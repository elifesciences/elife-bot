from lettuce import *


@step("I have imported the article_structure module")
def step_impl(step):
    import provider.article_structure as article_structure
    world.article_structure = article_structure


@step("I create an ArticleStructure with (\S+)")
def step_impl(step, filename):
    world.article = world.article_structure.ArticleStructure(filename)

@step("It exposes the correct (\S+), (\S+), (\S+) and (\S+)")
def step_impl(step, filename, extension, file_type, f_id):
    assert world.article.file_type == file_type
    assert world.article.extension == extension
    assert world.article.file_type == file_type
    assert world.article.f_id == f_id