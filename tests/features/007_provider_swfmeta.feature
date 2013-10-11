Feature: Use swfmeta as a data provider
  In order to use swfmeta as a data provider
  As a worker
  I want to parse execution history data and get useful results

  Scenario: Check if a workflow is open
    Given I have imported the SWFMeta provider module
    And I have the domain <domain>
    And I have the workflow name <workflow_name>
    And I have the workflow id <workflow_id>
    And I have a document <document>
    And I get JSON from the document
    And I parse the JSON string
    When I check is workflow open using the SWFMeta provider
    Then I get is open <is_open>

  Examples:
   | domain  | workflow_name | workflow_id  | document                                | is_open
   | Publish | S3Monitor     | None         | test_data/open_workflow_executions.json | True

  Scenario: Get the startTimestamp of the last completed workflow
    Given I have imported the SWFMeta provider module
    And I have the domain <domain>
    And I have the workflow name <workflow_name>
    And I have the workflow id <workflow_id>
    And I have a document <document>
    And I get JSON from the document
    And I parse the JSON string
    When I get last completed workflow execution startTimestamp using the SWFMeta provider
    Then I get the startTimestamp <startTimestamp>

  Examples:
   | domain  | workflow_name | workflow_id | document                                     | startTimestamp
   | Publish | S3Monitor     | None        | test_data/completed_workflow_executions.json | 1371047538.231