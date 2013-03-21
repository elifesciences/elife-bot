Feature: Parse an activity from Amazon SWF using a worker
	In order to use Amazon SWF
  As a worker
	I want to parse the decision response
	
	Scenario: Parse activity response for taskToken
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a worker module
	  When I get the taskToken using a worker
	  Then I have the taskToken <taskToken>
		
  Examples:
    | document    										| taskToken
    | test_data/activity.json					| AAAAKgAAAAEAAAAAAAAAAiTLU1nb+mIAOocBiGYTsSABMWaY3FM6Ib1SU1w+SRp1WIYxSmbtunYFMcfJs0LqS4bYWhNsYZIkrH7XGRwkgqx8IDM9o6m8BT9sQVUM6NRNxsbZlFUxFh1p6vpXVHWt64hB/9WvlrF8qWNR+gx9HTkCHJyfEdsk+3PFCjApQ6+YBtdZLmRw3iHLVT45LvuFnwdBCP+bk5ACOcYi8hcm89qVKMBjtLjZTDN0BAVyFX1/V+7zFnaEzrqErdcirHBA7/PHdcsYJpA1V37drsAL50N9U6MVMaYWmFlP7IPJPY4M

	Scenario: Parse activity response for activityType
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a worker module
	  When I get the activityType
	  Then I have the activityType <activityType>
	  And when I get the activity_name
	  Then I have the activity_name <activity_name> 

  Examples:
    | document    										| activityType				| activity_name
    | test_data/activity.json					| Sum									| activity_Sum

	Scenario: Parse activity response for input
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a worker module
	  When I get the input using a worker
	  Then input contains <element>
	  And input element <element> is instanceof <datatype>

  Examples:
    | document    										| element				| datatype
    | test_data/activity.json					| data					| list