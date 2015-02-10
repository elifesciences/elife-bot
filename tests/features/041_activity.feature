Feature: Activity class can be instantiated
	In order to use an activity
  As a user
	I want to confirm the activity class can be instantiated
	
	Scenario: Check an activity class builds and has correct properties
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name <activity_name>
		And I have an activity object
	  Then I can get a domain from the activity
		And I can get a task_list from the activity
		And I get the activity name <activity_name>
		
  Examples:
    | env					| activity_name				
    | dev					| PingWorker					
    | dev					| Sum									
    | live				| PingWorker
    | live				| Sum		

	Scenario: Check individual activity do_action results
		Given I have the activity name <activity_name>
		And I have an activity object
    And I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
	  Then I get a result from the activity <result>
		
  Examples:
    | activity_name				| document					                          | result
    | PingWorker					| test_data/activity.PingWorker.data.json			| True
    | Sum									| test_data/activity.Sum.data.json            | 6