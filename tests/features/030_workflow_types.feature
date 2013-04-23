Feature: Workflow is configured at Amazon SWF
	In order to use an Amazon SWF workflow
  As a user
	I want to confirm the workflow type exists
	
	Scenario: Check the workflow type exists in the SWF domain
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
    And I have imported the boto module
    And I have imported the boto.swf module
		And I have the workflow name <workflow_name>
	  When I connect to Amazon SWF
		And I have a workflow object
		And I have the workflow version
	  Then I can describe the SWF workflow type
		Finally I can disconnect from Amazon SWF
		
  Examples:
    | env					| workflow_name	
    | dev					| Ping
    | dev					| Sum
    | dev					| PublishArticle
    | live				| Ping
    | live				| PublishArticle
