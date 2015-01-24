Feature: UnzipArticleFiguresPDF activity
  In order to use the UnzipArticleFiguresPDF activity
  As a user
  I want to confirm the activity class can be used
  
  Scenario: Instantiate an UnzipArticleFiguresPDF object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    When I have the activity name UnzipArticleFiguresPDF
    Then I have an activity object
    And I get a filesystem provider from the activity object
    
  Examples:
    | env          
    | dev          
    
  Scenario: Get S3 object key from UnzipArticleFiguresPDF object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have the activity name UnzipArticleFiguresPDF
    And I have the activityId <activityId>
    And I have an activity object
    And I have the elife_id <elife_id>
    And I have the document name <document_name>
    When I read document to content with the activity object
    And I get the document from the activity object
    And I get the document name from path using the activity object
    And I get the pdf object S3key name from the activity object
    Then I have the S3key_name <S3key_name>
    
  Examples:
    | env          | activityId                    | elife_id   | document_name                    | S3key_name
    | dev          | UnzipArticleFiguresPDF_00534  | 00778      | test_data/elife00778-figures.zip | /elife-articles/00778/figures-pdf/elife00778-figures.pdf
