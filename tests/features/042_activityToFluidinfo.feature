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
		
	Scenario: Read and write an article XML file then parse it
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
		And I have an activity object
    And I have the document name <document_name>
		And I read the file named document name with ArticleToFluidinfo
		And I write the content from ArticleToFluidinfo to <filename>
		And I parse the document name with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| document_name					        | filename					| doi
    | dev  				| test_data/elife00013.xml			| elife00013.xml		| 10.7554/eLife.00013

	Scenario: Extract an article zip file, read and write the article XML file then parse it
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
		And I have an activity object
    And I have the document name <document_name>
		And I read the file named document name with ArticleToFluidinfo
		And I get the document name from ArticleToFluidinfo
		And I parse the document name with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| document_name					        					| filename					| doi
    | dev  				| test_data/elife_2013_00415.xml.zip			| elife00415.xml		| 10.7554/eLife.00415