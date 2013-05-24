Feature: Workflow class can be instantiated
	In order to use an workflow
  As a user
	I want to confirm the workflow class can be instantiated
	
	Scenario: Check an workflow class builds and has correct properties
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the workflow name <workflow_name>
		When I have a workflow object
	  Then I can get a domain from the workflow
		And I can get a task_list from the workflow
		And I get the workflow name <workflow_name>
		
  Examples:
    | env					| workflow_name				
    | dev					| Ping					
    | dev					| Sum									
    | dev					| PublishArticle
    | live				| Ping					
    | live				| Sum									
    | live				| PublishArticle