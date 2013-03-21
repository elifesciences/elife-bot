Feature: Parse a decision from Amazon SWF
	In order to use Amazon SWF
  As a decider
	I want to parse the decision response
	
	Scenario: Parse decision response for taskToken
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a decider module
	  When I get the taskToken using a decider
	  Then I have the taskToken <taskToken>
		
  Examples:
    | document    										| taskToken
    | test_data/decision.json					| AAAAKgAAAAEAAAAAAAAAAjaHv5Lk1csWNpSpgCC0bOKbWQv8HfmDMCyp6HvCbcrjeH2ao+M+Jz76e+wNukEX6cyLCf+LEBQmUy83b6Abd1HhduEQ/imaw2YftjNt20QtS75QXgPzOIFQ6rh43MKDwBCcnUpttjUzqieva2Y1eEisq4Ax7pZ+ydKmYBFodCvt48BPFD48L7qtmh14rpF2ic8AuNakilIhG3IL5s/UX1gMLre39Rd03UgK+0KuozCIfXwSU+wILRuSOaNB7cHDhiBFg12FSrUFXRHZVZr/qFhGXCEmLNjf/rOpNC1UoZwV

	Scenario: Parse decision response for workflowType
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a decider module
	  When I get the workflowType
	  Then I have the workflowType <workflowType> 

  Examples:
    | document    										| workflowType
    | test_data/decision.json					| Sum

	Scenario: Parse decision response for input
    Given I have a response JSON document <document>
		And I get JSON from the document
		And I parse the JSON string
		And I have a decider module
	  When I get the input using a decider
	  Then input contains <element>
	  And input element <element> is instanceof <datatype>

  Examples:
    | document    										| element				| datatype
    | test_data/decision.json					| data					| list