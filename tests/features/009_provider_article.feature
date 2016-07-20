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
    | dev | 10.7554/eLife.00013  | 00013   | http://dx.doi.org/10.7554/eLife.00013 | http://lens.elifesciences.org/00013 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.00013+%40eLife

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
    And I have the article is in display channel "Research article" <display_channel_one>
    And I have the article is in display channel "Feature article" <display_channel_two>
    And I have the article authors string <authors_string>

  Examples:
    | env | tmp_base_dir  | test_name        | document_name                  | doi                  | doi_id  | doi_url                               | lens_url                            | tweet_url                                                                            | pub_date_timestamp | article_type     | related_article_count | xlink_href          | is_poa  | insight_doi          | display_channel_one | display_channel_two | authors_string
    | dev | tmp           | article_provider | test_data/elife00013.xml	      | 10.7554/eLife.00013  | 00013   | http://dx.doi.org/10.7554/eLife.00013 | http://lens.elifesciences.org/00013 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.00013+%40eLife | 1350259200           | research-article | 1                     | 10.7554/eLife.00242 | False   | 10.7554/eLife.00242  | True                | False               | Rosanna A Alegado, Laura W Brown, Shugeng Cao, Renee K Dermenjian, Richard Zuzow, Stephen R Fairclough, Jon Clardy, Nicole King
    | dev | tmp           | article_provider | test_data/elife_poa_e03977.xml | 10.7554/eLife.03977  | 03977   | http://dx.doi.org/10.7554/eLife.03977 | http://lens.elifesciences.org/03977 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.03977+%40eLife | None                 | research-article | 0                     | None                | True    | None                 | True                | False               | Xili Liu, Xin Wang, Xiaojing Yang, Sen Liu, Lingli Jiang, Yimiao Qu, Lufeng Hu, Qi Ouyang, Chao Tang
    | dev | tmp           | article_provider | test_data/elife04796.xml       | 10.7554/eLife.04796  | 04796   | http://dx.doi.org/10.7554/eLife.04796 | http://lens.elifesciences.org/04796 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.04796+%40eLife | 1437004800           | research-article | 0                     | None                | False   | None                 | False               | False               | Steven Fiering, Lay-Hong Ang, Judith Lacoste, Tim D Smith, Erin Griner, Reproducibility Project: Cancer Biology
    | dev | tmp           | article_provider | test_data/elife09169.xml       | 10.7554/eLife.09169  | 09169   | http://dx.doi.org/10.7554/eLife.09169 | http://lens.elifesciences.org/09169 | http://twitter.com/intent/tweet?text=http%3A%2F%2Fdx.doi.org%2F10.7554%2FeLife.09169+%40eLife | 1433721600           | correction       | 1                     | 10.7554/eLife.06959 | False   | None                 | False               | False               | Irawati Kandela, James Chou, Kartoa Chow, Reproducibility Project: Cancer Biology

  Scenario: Given S3 bucket data, use the article provider to get a list of DOI id that were ever POA articles
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have a document <folder_names>
    And I get JSON from the document
    And I parse the JSON string
    And I set the world attribute folder_names to world json
    And I have a document <s3_key_names>
    And I get JSON from the document
    And I parse the JSON string
    And I set the world attribute s3_key_names to world json
    And I have a document <poa_doi_ids>
    And I get JSON from the document
    And I parse the JSON string
    And I set the world attribute poa_doi_ids to world json
    When I get was poa doi ids using the article provider
    Then I have poa doi ids equal to world was poa doi ids
    And I check was ever poa 99999 using the article provider
    Then I get was ever poa is False
    And I check was ever poa 01257 using the article provider
    Then I get was ever poa is True

  Examples:
    | env | folder_names                              | s3_key_names                              | poa_doi_ids
    | dev | test_data/poa_published_folder_names.json | test_data/poa_published_s3_key_names.json | test_data/poa_was_poa_doi_ids.json
    
  Scenario: Given article XML S3 key names for POA articles, get the doi id
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have an s3 key name <s3_key_name>
    When I get doi id from poa s3 key name using the article provider
    Then I get doi_id <doi_id>

  Examples:
    | env | s3_key_name                                      | doi_id  
    | dev | published/20140508/elife_poa_e02419.xml          | 2419
    | dev | published/20140508/elife_poa_e02444v2.xml        | 2444
    | dev | pubmed/published/20140917/elife_poa_e03970.xml   | 3970
    
    
  Scenario: Given article XML S3 key names for VOR articles, get the doi id
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have an s3 key name <s3_key_name>
    When I get doi id from s3 key name using the article provider
    Then I get doi_id <doi_id>

  Examples:
    | env | s3_key_name                                | doi_id  
    | dev | pubmed/published/20140923/elife02104.xml   | 2104
    | dev | pubmed/published/20141224/elife04034.xml   | 4034
    
  Scenario: Given article XML S3 key name and the folder prefix, get the date string from the published folder
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have the prefix <prefix>
    And I have an s3 key name <s3_key_name>
    When I get date string from s3 key name using the article provider
    Then I get the date string <date_string>

  Examples:
    | env | prefix              | s3_key_name                                | date_string  
    | dev | pubmed/published/   | pubmed/published/20140923/elife02104.xml   | 20140923
    | dev | pubmed/published/   | pubmed/published/20141224/elife04034.xml   | 20141224
    | dev | published/          | published/20140508/elife_poa_e02444v2.xml  | 20140508
    
  Scenario: Given S3 bucket data, use the article provider to get the date the article was published
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I create an article provider
    And I have a document test_data/pubmed_published_folder_names.json
    And I get JSON from the document
    And I parse the JSON string
    And I set the world attribute folder_names to world json
    And I have a document test_data/pubmed_published_s3_key_names.json
    And I get JSON from the document
    And I parse the JSON string
    And I set the world attribute s3_key_names to world json
    And I have a doi <doi>
    And I have the pub event type <pub_event_type>
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    When I get article bucket published dates using the article provider
    And I get article bucket pub date using the article provider
    And I get the date string from the pub date
    Then I get the date string <date_string>
    
  Examples:
    | env | doi                  | pub_event_type | date_string
    | dev | 10.7554/eLife.05125  | POA            | 2014-12-23T00:00:00.000Z
    | dev | 10.7554/eLife.05125  | VOR            | 2015-01-17T00:00:00.000Z
    | dev | 10.7554/eLife.02236  | VOR            | 2014-09-15T00:00:00.000Z
    | dev | 10.7554/eLife.04551  | POA            | 2014-11-12T00:00:00.000Z
    | dev | 10.7554/eLife.00662  | VOR            | 2015-02-03T00:00:00.000Z
    | dev | 10.7554/eLife.99999  | POA            | None
    