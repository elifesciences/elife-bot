Feature: Use EJP data provider
  In order to use EJP as a data provider
  As a worker
  I want to parse files from local block storage device
  
  Scenario: Open a file with EJP provider' filesystem provider
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a ejp provider
    And I have a document <document>
    And I have the filename <filename>
    When I parse author file the document with ejp
    And I get the ejp fs document
    Then I have the ejp document <ejp_document>

  Examples:
    | tmp_base_dir  | test_name       | document                      | filename    | ejp_document 
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | authors.csv | authors.csv

  Scenario: Parse an author file with EJP provider and check column headings
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a ejp provider
    And I have a document <document>
    When I parse author file the document with ejp
    Then I have the column headings <column_headings>

  Examples:
    | tmp_base_dir  | test_name       | document                      | column_headings
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | ['ms_no', 'ms_title', 'author_seq', 'first_nm', 'last_nm', 'author_type_cde', 'dual_corr_author_ind', 'e_mail']
    
  Scenario: Parse an author file with EJP provider and count the author rows returned
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a ejp provider
    And I have a document <document>
    And I have the doi id <doi_id>
    And I have corresponding <corr>
    When I get the authors from ejp
    Then I have the authors count <count>

  Examples:
    | tmp_base_dir  | test_name       | document                      | doi_id | corr | count
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | None   | None | 7
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | 00003  | None | 3
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | 00003  | True | 1
    | tmp           | ejp_author_file | test_data/ejp_author_file.csv | 13     | True | 2
    
  Scenario: Get the S3 key name for the latest file given bucket JSON data
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have file type <file_type>
    And I have a document <document>
    And I get JSON from the document
    And I parse the JSON string
    And I create a ejp provider
    When I find latest s3 file name using ejp
    Then I have s3 file name <s3_file_name>

  Examples:
    | tmp_base_dir  | file_type | document                       | s3_file_name
    | tmp           | author    | test_data/ejp_bucket_list.json | ejp_query_tool_query_id_152_15a)_Accepted_Paper_Details_2013_10_31_eLife.csv
    | tmp           | editor    | test_data/ejp_bucket_list.json | ejp_query_tool_query_id_158_15b)_Accepted_Paper_Details_2013_10_31_eLife.csv

  Scenario: Parse an editor file with EJP provider and check column headings
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a ejp provider
    And I have a document <document>
    When I parse editor file the document with ejp
    Then I have the column headings <column_headings>

  Examples:
    | tmp_base_dir  | test_name       | document                      | column_headings
    | tmp           | ejp_editor_file | test_data/ejp_editor_file.csv | ['ms_no', 'ms_title', 'first_nm', 'last_nm', 'e_mail']
    
  Scenario: Parse an editor file with EJP provider and count the author rows returned
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a ejp provider
    And I have a document <document>
    And I have the doi id <doi_id>
    When I get the editors from ejp
    Then I have the editors count <count>

  Examples:
    | tmp_base_dir  | test_name       | document                      | doi_id | count
    | tmp           | ejp_editor_file | test_data/ejp_editor_file.csv | None   | 2
    | tmp           | ejp_editor_file | test_data/ejp_editor_file.csv | 00003  | 1
    | tmp           | ejp_editor_file | test_data/ejp_editor_file.csv | 13     | 1
