Feature: Activity type is configured at Amazon SWF
	In order to use an Amazon SWF activity
  As a user
	I want to confirm the activity type exists
	
	Scenario: Check the workflow type exists in the SWF domain
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
    And I have imported the boto module
    And I have imported the boto.swf module
		And I have the activity name <activity_name>
		And I have the activity version <activity_version>
	  When I connect to Amazon SWF
	  Then I can describe the SWF activity type
		Finally I can disconnect from Amazon SWF
		
  Examples:
    | env					| activity_name				| activity_version
    | dev					| PingWorker					| 1
    | dev					| Sum									| 1
    | dev					| ArticleToFluidinfo	| 1
    | live				| Ping								| 1
    | live				| ArticleToFluidinfo	| 1
