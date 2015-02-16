Feature: Use article provider
  In order to use the article provider
  As a worker
  I want to parse article XML and get useful data in return
  
  Scenario: Given a DOI, turn it into some values, without parsing XML
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    When I have a doi <doi>
    Then I get a doi id from the article provider <doi_id>
    And I get a DOI url from the article provider <doi_url>
    And I get a lens url from the article provider <lens_url>
    And I get a tweet url from the article provider <tweet_url>

  Examples:
    | env | doi                  | doi_id  | doi_url                               | lens_url                            | tweet_url      
    | dev | 10.7554/eLife.00013  | 00013   | http://dx.doi.org/10.7554/eLife.00013 | http://lens.elifesciences.org/00013 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.00013

  Scenario: Given an article XML, parse it and return some values
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create an article provider
    And I have the document name <document_name>
    When I parse the document with the article provider
    Then I have the article doi <doi>
    And I have the article doi_id <doi_id>
    And I have the article doi_url <doi_url>
    And I have the article lens_url <lens_url>
    And I have the article tweet_url <tweet_url>
    And I have the article pub_date_timestamp <pub_date_timestamp>
    And I have the article article_type <article_type>

  Examples:
    | env | tmp_base_dir  | test_name        | document_name	          | doi                  | doi_id  | doi_url                               | lens_url                            | tweet_url                                                                            | pub_date_timestamp | article_type
    | dev | tmp           | article_provider | test_data/elife00013.xml	| 10.7554/eLife.00013  | 00013   | http://dx.doi.org/10.7554/eLife.00013 | http://lens.elifesciences.org/00013 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.00013 | 1350259200         | research-article
