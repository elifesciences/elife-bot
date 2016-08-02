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
