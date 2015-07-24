Feature: PackagePOA activity
  In order to use the PackagePOA activity
  As a user
  I want to confirm the activity class can be used

  Scenario: Instantiate an PackagePOA object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    When I have the activity name PackagePOA
    And I have the activityId PackagerPOA_test
    Then I have an activity object
    And I get a ejp provider from the activity object

  Examples:
    | env          
    | dev          
