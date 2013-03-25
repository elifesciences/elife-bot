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
		And I have the workflow version <workflow_version>
	  When I connect to Amazon SWF
	  Then I can describe the SWF workflow type
		Finally I can disconnect from Amazon SWF
		
  Examples:
    | env					| workflow_name				| workflow_version
    | dev					| Ping								| 1
    | dev					| Sum									| 1
    | dev					| PublishArticle			| 1
    | live				| Ping								| 1
    | live				| PublishArticle			| 1
