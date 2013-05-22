Feature: Use Amazon AWS via boto
	In order to use Amazon AWS
  As a user
	I want to communicate with Amazon AWS
	
	Scenario: Connect to Amazon SWF
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
    And I have imported the boto module
    And I have imported the boto.swf module
	  When I connect to Amazon SWF
	  Then I can describe the SWF domain
		Finally I can disconnect from Amazon SWF
		
  Examples:
    | env
    | dev
    | live
		
	Scenario: Connect to Amazon SimpleDB
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
	  And I have the simpledb region from the settings
    And I have imported the boto module
    And I have imported the boto.sdb module
	  When I connect to Amazon SimpleDB
	  Then I can list the SimpleDB domains
		Finally I can disconnect from Amazon SimpleDB
		
  Examples:
    | env
    | dev
    | live