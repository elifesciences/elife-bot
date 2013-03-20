Feature: Provide settings for Amazon AWS
	In order to use Amazon AWS
  As a user
	I want to import the required settings
	
	Scenario: Check required settings
    Given I have imported a settings module
		And I have the settings environment <env>
	  When I get the settings
	  Then I have a setting for <identifier> 
		
  Examples:
    | env        	| identifier
    | dev					| aws_access_key_id
    | dev					| aws_secret_access_key
    | dev					| domain
    | dev					| default_task_list

		| live				| aws_access_key_id
    | live				| aws_secret_access_key
    | live				| domain
    | live				| default_task_list
		