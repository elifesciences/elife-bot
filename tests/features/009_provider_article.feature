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

  Scenario: Given an article DOI get the article lookup URL from the article provider
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have a doi_id <doi_id>
    When I get article lookup url with the article provider
    Then I have lookup url <lookup_url>
    
  Examples:
    | env | doi_id  | lookup_url                
    | dev | 3       | http://elifesciences.org/lookup/doi/10.7554/eLife.00003

  Scenario: Given article details check if it is published from the article provider
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have a doi <doi>
    And I have is poa <is_poa>
    And I have was ever poa <was_ever_poa>
    And I have the article url <article_url>
    When I check is article published with the article provider
    Then I have is published <is_published>

  Examples:
    | env | doi                  | is_poa   | was_ever_poa  | article_url                                                    | is_published
    | dev | 10.7554/eLife.00003  | True     | True          | Test_None                                                      | False
    | dev | 10.7554/eLife.00003  | False    | False         | Test_None                                                      | False
    | dev | 10.7554/eLife.00003  | False    | True          | Test_None                                                      | False
    | dev | 10.7554/eLife.00003  | False    | None          | Test_None                                                      | False
    | dev | 10.7554/eLife.00003  | True     | True          | http://elifesciences.org/content/early/2012/01/01/eLife.00003  | True
    | dev | 10.7554/eLife.00003  | False    | False         | http://elifesciences.org/content/1/e00003                      | True
    | dev | 10.7554/eLife.00003  | False    | None          | http://elifesciences.org/content/1/e00003                      | True
    | dev | 10.7554/eLife.00003  | False    | True          | http://elifesciences.org/content/early/2012/01/01/eLife.00003  | False
    | dev | 10.7554/eLife.00003  | True     | None          | http://elifesciences.org/content/early/2012/01/01/eLife.00003  | True
    | dev | 10.7554/eLife.00003  | True     | None          | Test_None                                                      | False

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
    And I count the total related articles as <related_article_count>
    And I have the article related article index 0 xlink_href <xlink_href>
    And I have the article is poa <is_poa>
    And I have the article related insight doi <insight_doi>
    And I have the article authors string <authors_string>

  Examples:
    | env | tmp_base_dir  | test_name        | document_name                  | doi                  | doi_id  | doi_url                               | lens_url                            | tweet_url                                                                            | pub_date_timestamp | article_type     | related_article_count | xlink_href          | is_poa  | insight_doi          | authors_string
    | dev | tmp           | article_provider | test_data/elife00013.xml	      | 10.7554/eLife.00013  | 00013   | http://dx.doi.org/10.7554/eLife.00013 | http://lens.elifesciences.org/00013 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.00013 | 1350259200           | research-article | 1                     | 10.7554/eLife.00242 | False   | 10.7554/eLife.00242  | Rosanna A Alegado, Laura W Brown, Shugeng Cao, Renee K Dermenjian, Richard Zuzow, Stephen R Fairclough, Jon Clardy, Nicole King
    | dev | tmp           | article_provider | test_data/elife_poa_e03977.xml | 10.7554/eLife.03977  | 03977   | http://dx.doi.org/10.7554/eLife.03977 | http://lens.elifesciences.org/03977 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.03977 | 0                   | research-article | 0                     | None                | True    | None                 | Xili Liu, Xin Wang, Xiaojing Yang, Sen Liu, Lingli Jiang, Yimiao Qu, Lufeng Hu, Qi Ouyang, Chao Tang
