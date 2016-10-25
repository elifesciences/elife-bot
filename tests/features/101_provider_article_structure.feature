Feature: Use article_structure as to examine filenames
  In order to use ArticleStructure to examine filenames
  As a script
  I want ArticleStructure to parse the filename and return useful information

  @wip
  Scenario: Obtain basic information from a full filename
    Given I have imported the article_structure module
    When I create an ArticleStructure with <full_filename>
    Then It exposes the correct <filename>, <extension>, <file_type> and <article_id>

  Examples:
    | full_filename                        | filename              | extension  | file_type   | article_id
    | elife-00012-vor-r1.zip               | elife-00012-vor-r1    | zip        | ArticleZip  | 00012
    | elife-00123-poa.zip                  | elife-00123-poa       | zip        | ArticleZip  | 00123
    | elife-00288-supp-v1.zip              | elife-00288-supp-v1   | zip        | Other       | 00288
    | elife-00012-v1.xml                   | elife-00012-v1        | xml        | ArticleXML  | 00012
    | elife-00012-fig3-figsupp1.tiff  | elife-00012-fig3-figsupp1  | tiff | Figure | 00012

