Feature: Use article provider
  In order to use the article provider
  As a worker
  I want to parse article XML and get useful data in return

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
    