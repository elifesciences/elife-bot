Feature: S3Monitor activity
	In order to use the S3Monitor activity
  As a user
	I want to confirm the activity class can be used
	
	Scenario: Get a log item name for a SimpleDB item
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name S3Monitor
		And I have an activity object
    And I have the item name <item_name>
		And I have the item attr last_modified_timestamp <last_modified_timestamp>
	  Then I get the log_item_name from the S3Monitor <log_item_name>
		
  Examples:
    | env  | item_name                            | last_modified_timestamp   | log_item_name
    | dev  | elife-articles/00003/elife00003.xml  | 1359244240                | 1359244240_elife-articles/00003/elife00003.xml
		
	Scenario: Get extended date values from a timestamp
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name S3Monitor
		And I have an activity object
		And I have the base name <base_name>
		And I have the timestamp <timestamp>
		And I have the date format <date_format>
		And I get the expanded date attributes from S3Monitor using a timestamp
		#Then I have the timestamp attribute <timestamp>
		And I have the date attribute <date>
		And I have the year attribute <year>
		And I have the month attribute <month>
		And I have the day attribute <day>
		And I have the time attribute <time>
		
  Examples:
    | env  | base_name     | timestamp   | date_format             | date                      | year | month | day | time
    | dev  | last_modified | 1359244237  | %Y-%m-%dT%H:%M:%S.000Z  | 2013-01-26T23:50:37.000Z  | 2013 | 01    | 26  | 23:50:37