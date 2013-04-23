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
	  When I connect to Amazon SWF
		And I have an activity object
		And I have the activity version
	  Then I can describe the SWF activity type
		Finally I can disconnect from Amazon SWF
		
  Examples:
    | env					| activity_name				
    | dev					| PingWorker					
    | dev					| Sum									
    | dev					| ArticleToFluidinfo	
    | live				| PingWorker					
    | live				| ArticleToFluidinfo	
