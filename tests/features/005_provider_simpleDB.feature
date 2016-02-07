Feature: Use SimpleDB as a data provider
  In order to use SimpleDB as a data provider
  As a worker
  I want to access domains and process data
  
  Scenario: Check SimpleDB apostrophe escape function
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have imported the SimpleDB provider module
    When I have the val <val>
    And I use SimpleDB to escape the val
    Then I have the escaped val <escaped_val>

  Examples:
    | env    | val           | escaped_val
    | dev    | test          | test
    | dev    | 123           | 123
    | dev    | O'Reilly      | O''Reilly

  Scenario: Get a SimpleDB domain name for a particular environment
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have a setting for <postfix>
    And I get a setting for postfix <postfix>
    And I have imported the SimpleDB provider module
    When I get the domain name from the SimpleDB provider for <domain>
    Then I have a domain name equal to the domain plus the postfix

  Examples:
    | env    | postfix                 | domain
    | dev    | simpledb_domain_postfix | S3File
    | dev    | simpledb_domain_postfix | S3FileLog
    | live   | simpledb_domain_postfix | S3File
    | live   | simpledb_domain_postfix | S3FileLog
    
  Scenario: Build SimpleDB queries for elife articles bucket
    Given I have imported the SimpleDB provider module
    And I have the domain name S3FileLog_dev
    And I have the file data types ["xml", "pdf", "img", "suppl", "video", "svg", "figures"]
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    And I have the bucket name elife-articles
    And I have the file data type <file_data_type>
    And I have the doi id <doi_id>
    And I have the last updated since <last_updated_since>
    When I get the query from the SimpleDB provider
    Then I have the SimpleDB query <query>
  
  Examples:
    | file_data_type | doi_id | last_updated_since       | query
    | None           | None   | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name is not null order by name asc
    | xml            | None   | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.xml%' order by name asc
    | figures        | None   | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%figures%' order by name asc
    | None           | 00013  | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '00013/%' order by name asc
    | None           | None   | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and last_modified_timestamp > '1356998400' and name is not null order by name asc
    | xml            | 00013  | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.xml%' and name like '00013/%' order by name asc
    | svg            | 00013  | None                     | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.svg%' and name like '00013/%' order by name asc
    | None           | 00013  | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '00013/%' and last_modified_timestamp > '1356998400' order by name asc
    | xml            | None   | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.xml%' and last_modified_timestamp > '1356998400' order by name asc
    | xml            | 00013  | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.xml%' and name like '00013/%' and last_modified_timestamp > '1356998400' order by name asc
    | svg            | 00013  | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%.svg%' and name like '00013/%' and last_modified_timestamp > '1356998400' order by name asc
    | figures        | 00778  | 2013-01-01T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-articles' and name like '%figures%' and name like '00778/%' and last_modified_timestamp > '1356998400' order by name asc
    
  Scenario: Get the latest S3 files from SimpleDB provider and count results
    Given I have imported the SimpleDB provider module
    And I have the file data types ["xml", "pdf", "img", "suppl", "video", "svg"]
    And I have a document <document>
		And I get JSON from the document
		And I parse the JSON string
    When I get the latest article S3 files from SimpleDB
    Then I have an item list count <count>

  Examples:
    | document                                                  | count
    | test_data/provider.simpleDB.elife_articles.latest01.json  | 20   
    | test_data/provider.simpleDB.elife_articles.latest02.json  | 4     
    
  Scenario: Get the latest S3 files from SimpleDB provider and check values
    Given I have imported the SimpleDB provider module
    And I have the file data types ["xml", "pdf", "img", "suppl", "video", "svg"]
    And I have a document <document>
		And I get JSON from the document
		And I parse the JSON string
    When I get the latest article S3 files from SimpleDB
    Then the item list <index> <key> is <value>
    
  Examples:
    | document                                                  | index | key                     | value
    | test_data/provider.simpleDB.elife_articles.latest01.json  | 10    | name                    | 00005/elife_2012_00005.video.zip
    | test_data/provider.simpleDB.elife_articles.latest01.json  | 3     | name                    | 00003/elife_2012_00003.xml.zip
    | test_data/provider.simpleDB.elife_articles.latest01.json  | 8     | name                    | 00005/elife_2012_00005.pdf.zip
    | test_data/provider.simpleDB.elife_articles.latest01.json  | 8     | last_modified_timestamp | 1359244876
    | test_data/provider.simpleDB.elife_articles.latest02.json  | 0     | name                    | 00003/elife_2012_00003.xml.zip
    | test_data/provider.simpleDB.elife_articles.latest02.json  | 3     | name                    | 00048/elife_2012_00048.xml.r6.zip
    | test_data/provider.simpleDB.elife_articles.latest02.json  | 1     | name                    | 00005/elife00005.xml
    | test_data/provider.simpleDB.elife_articles.latest02.json  | 1     | last_modified_timestamp | 1359244983
    
  Scenario: Build SimpleDB queries for email queue
    Given I have imported the SimpleDB provider module
    And I have the domain name EmailQueue_dev
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    And I have the sort by <sort_by>
    And I have the query type <query_type>
    And I have the limit <limit>
    And I have the sent status <sent_status>
    And I have the email type <email_type>
    And I have the doi id <doi_id>
    And I have the date scheduled before <date_scheduled_before>
    And I have the date sent before <date_sent_before>
    And I have the recipient email <recipient_email>
    When I get the email queue query from the SimpleDB provider
    Then I have the SimpleDB query <query>
  
  Examples:
    | sort_by              | query_type | limit  | sent_status | email_type | doi_id | date_scheduled_before    | date_sent_before   | recipient_email   | query
    | None                 | None       | None   | None        | None       | None   | None                     | None               | None              | select * from EmailQueue_dev where sent_status is null
    | date_added_timestamp | items      | None   | None        | None       | None   | None                     | None               | None              | select * from EmailQueue_dev where sent_status is null and date_added_timestamp is not null order by date_added_timestamp asc
    | None                 | count      | None   | None        | None       | None   | None                     | None               | None              | select count(*) from EmailQueue_dev where sent_status is null
    | None                 | count      | None   | None        | None       | None   | 1970-01-01T00:00:01.000Z | None               | None              | select count(*) from EmailQueue_dev where sent_status is null and date_scheduled_timestamp < '1'
    
  Scenario: Get a unique item_name for an email queue SimpleDB object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have imported the SimpleDB provider module
    And I connect to SimpleDB using the SimpleDB provider
    And I have the domain name EmailQueue
    And I have the check is unique <check_is_unique>
    And I have the timestamp <timestamp>
    And I have the doi id <doi_id>
    And I have the email type <email_type>
    And I have the recipient email <recipient_email>
    When I get the unique email queue item_name from the SimpleDB provider
    Then I have the unique item name <unique_item_name>
  
  Examples:
    | env  | timestamp | check_is_unique | doi_id   | email_type  | recipient_email    | unique_item_name
    | dev  | 1         | None            | None     | None        | None               | 1
    | dev  | 1         | None            | 00003    | example     | elife@example.com  | 1__00003__example__elife@example.com
    # Next example checks live SimpleDB and expects a record with item_name = 1, disable for speed
    # | dev  | 1         | True            | None     | None        | None               | 1__001
    
  Scenario: Prepare an item to add to the email queue SimpleDB object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have imported the SimpleDB provider module
    And I have add value <add>
    And I have the email type <email_type>
    And I have the recipient email <recipient_email>
    And I have the sender email <sender_email>
    When I add email to email queue with the SimpleDB provider
    Then I get item attributes date_scheduled_timestamp <date_scheduled_timestamp>
  
  Examples:
    | env  | add    | email_type | recipient_email   | sender_email      | date_scheduled_timestamp
    | dev  | False  | test       | test@example.com  | test@example.com  | 0

  Scenario: Build SimpleDB queries for elife POA bucket
    Given I have imported a settings module
    And I have the settings environment dev
    And I get the settings
    And I have imported the SimpleDB provider module
    And I have the domain name S3FileLog_dev
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    And I have the bucket name elife-ejp-poa-delivery-dev
    And I have the last updated since <last_updated_since>
    When I get the generic bucket query from the SimpleDB provider
    Then I have the SimpleDB query <query>
  
  Examples:
    | last_updated_since       | query
    | None                     | select * from S3FileLog_dev where bucket_name = 'elife-ejp-poa-delivery-dev' and last_modified_timestamp is not null order by last_modified_timestamp desc
    | 2014-04-20T00:00:00.000Z | select * from S3FileLog_dev where bucket_name = 'elife-ejp-poa-delivery-dev' and last_modified_timestamp > '1397952000' order by last_modified_timestamp desc

  Scenario: Build SimpleDB queries for elife production final bucket
    Given I have imported a settings module
    And I have the settings environment dev
    And I get the settings
    And I have imported the SimpleDB provider module
    And I have the domain name S3FileLog
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    And I have the bucket name elife-production-final
    And I have the last updated since <last_updated_since>
    When I get the generic bucket query from the SimpleDB provider
    Then I have the SimpleDB query <query>
  
  Examples:
    | last_updated_since       | query
    | None                     | select * from S3FileLog where bucket_name = 'elife-production-final' and last_modified_timestamp is not null order by last_modified_timestamp desc
    | 2014-04-20T00:00:00.000Z | select * from S3FileLog where bucket_name = 'elife-production-final' and last_modified_timestamp > '1397952000' order by last_modified_timestamp desc


  Scenario: Build SimpleDB queries for elife lens jpg zip bucket
    Given I have imported a settings module
    And I have the settings environment dev
    And I get the settings
    And I have imported the SimpleDB provider module
    And I have the domain name S3FileLog
    And I have the date format %Y-%m-%dT%H:%M:%S.000Z
    And I have the bucket name elife-production-lens-jpg
    And I have the last updated since <last_updated_since>
    When I get the generic bucket query from the SimpleDB provider
    Then I have the SimpleDB query <query>
  
  Examples:
    | last_updated_since       | query
    | None                     | select * from S3FileLog where bucket_name = 'elife-production-lens-jpg' and last_modified_timestamp is not null order by last_modified_timestamp desc
    | 2014-04-20T00:00:00.000Z | select * from S3FileLog where bucket_name = 'elife-production-lens-jpg' and last_modified_timestamp > '1397952000' order by last_modified_timestamp desc
  