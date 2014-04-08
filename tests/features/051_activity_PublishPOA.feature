Feature: PublishPOA activity
  In order to use the PublishPOA activity
  As a user
  I want to confirm the activity class can be used

  Scenario: Instantiate an PublishPOA object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    When I have the activity name PublishPOA
    And I have the activityId PublishPOA_test
    Then I have an activity object

  Examples:
    | env          
    | dev          
