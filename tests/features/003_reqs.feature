Feature: Use python imports and requirements
  In order to use python
  As a user
  I want to import packages
  
  Scenario: Import python packages by name
    Given I have the package name <package_name>
    When I import the package
    Then I get the package with name <package_name>

  Examples:
    | package_name
    | requests
    | boto
    | jinja2
    | lxml
    | bs4
    | fom
    | elife-api-prototype
    | elife-poa-xml-generation
    | git
    | arrow
    | elementtree
    | PyPDF2
    | wsgiref
