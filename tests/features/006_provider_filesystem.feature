Feature: Use filesystem as a data provider
  In order to use filesystem as a data provider
  As a worker
  I want to create and use files from local block storage device
  
  Scenario: Unzip a file to find multiple files inside
    Given I have a tmp_base_dir <tmp_base_dir>
    And I have test name <test_name>
    And I get the current datetime
    And I get the tmp_dir from the world
    And I create a filesystem provider
    And I have a document <document>
    When I write the document to tmp_dir with filesystem
    And I get the filesystem document
    Then I have the filesystem document count <count>

  Examples:
    | tmp_base_dir  | test_name         | document                     | count
    | tmp           | filesystem_unzip  | test_data/multiple_files.zip | 3
