Feature: ExpandArticle activity
  In order to use the ExpandArticle activity
  As a user
  I want to confirm the activity class can be used

  Scenario: Instantiate an ExpandArticle object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    When I have the activity name ExpandArticle
    And I have the activityId ExpandArticle_test
    Then I have an activity object

  Examples:
    | env          
    | dev          


  Scenario: Get the update date from an article zip filename using an ExpandArticle activity object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have the activity name ExpandArticle
    And I have the activityId ExpandArticle_test
    And I have an activity object
    And I have the filename <filename>
    When I get update date from the filename using the activity object
    Then I see the string <update_date>
  
  Examples:
    | env | filename                                | update_date  
    | dev | elife-07702-vor-r4.zip                  | None    
    | dev | elife-00013-vor-v1-20121015000000.zip   | 2012-10-15T00:00:00Z

  Scenario: Get the version from an article zip filename using an ExpandArticle activity object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have the activity name ExpandArticle
    And I have the activityId ExpandArticle_test
    And I have an activity object
    And I have the filename <filename>
    When I get version from the filename using the activity object
    Then I see the string <version>
  
  Examples:
    | env | filename                                | version  
    | dev | elife-07702-vor-r4.zip                  | None    
    | dev | elife-00013-vor-v1-20121015000000.zip   | 1
