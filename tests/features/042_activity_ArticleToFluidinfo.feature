Feature: ArticleToFluidinfo activity
	In order to use the ArticleToFluidinfo activity
  As a user
	I want to confirm the activity class can be used
	
	Scenario: Parse an article XML document
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
		And I have an activity object
    And I have the document name <document_name>
		When I parse the document name with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| document_name					        | doi
    | dev  				| test_data/elife00013.xml			| 10.7554/eLife.00013
		
	Scenario: Read and write an article XML file then parse it
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
    And I have the activityId <activityId>
		And I have an activity object
		And I have the document name <document_name>
		And I have the filename <filename>
		When I read document to content with the activity object
		And I get the document path from the activity object
		And I parse the document path with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| activityId                | document_name					        | filename					| doi
    | dev  				| ArticleToFluidinfo_00013  | test_data/elife00013.xml			| elife00013.xml		| 10.7554/eLife.00013

	Scenario: Optionally download S3 file, optionally extract a zip file, read and write the article XML file then parse it
    Given I have imported a settings module
		And I have the settings environment <env>
	  And I get the settings
		And I have the activity name ArticleToFluidinfo
    And I have the activityId <activityId>
		And I have an activity object
    And I have the document name <document_name>
		And I have the filename <filename>
		When I read document to content with the activity object
		And I get the document path from the activity object
		And I parse the document path with ArticleToFluidinfo
	  Then I get the DOI from the ArticleToFluidinfo article <doi>
		
  Examples:
    | env  				| activityId                | document_name																															| filename			| doi
    | dev  				| ArticleToFluidinfo_00415  | test_data/elife_2013_00415.xml.zip																				| None					| 10.7554/eLife.00415
    | dev  				| ArticleToFluidinfo_00415  | https://s3.amazonaws.com/elife-articles/00415/elife_2013_00415.xml.zip		| None					| 10.7554/eLife.00415