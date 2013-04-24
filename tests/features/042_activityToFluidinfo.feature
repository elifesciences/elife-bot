Feature: ActivityToFluidinfo activity
	In order to use the ActivityToFluidinfo activity
  As a user
	I want to confirm the activity class can be used
	
	Scenario: Parse an article XML document
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
		And I have an activity object
    And I have the document name <document_name>
		And I parse the document name with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| document_name					        | doi
    | dev  				| test_data/elife00013.xml			| 10.7554/eLife.00013
