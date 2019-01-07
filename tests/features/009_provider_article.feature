Feature: Use article provider
  In order to use the article provider
  As a worker
  I want to parse article XML and get useful data in return

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
