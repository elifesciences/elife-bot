Feature: PublicationEmail activity
  In order to use the PublicationEmail activity
  As a user
  I want to confirm the activity class can be used

  Scenario: Instantiate an PublicationEmail object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    When I have the activity name PublicationEmail
    And I have the activityId PublicationEmail_test
    Then I have an activity object

  Examples:
    | env          
    | dev          


  Scenario: Choose the email type for the template used by an PublicationEmail object
    Given I have imported a settings module
    And I have the settings environment <env>
    And I get the settings
    And I have the activity name PublicationEmail
    And I have the activityId PublicationEmail_test
    And I have an activity object
    And I have the article type <article_type>
    And I have is poa <is_poa>
    And I have was ever poa <was_ever_poa>
    And I have the feature article False
    When I choose the email type using the activity object
    Then I get the email type <email_type>

  Examples:
    | env | article_type           | is_poa   | was_ever_poa   | email_type
    | dev | article-commentary     | False    | False          | author_publication_email_Insight_to_VOR
    | dev | research-article       | True     | True           | author_publication_email_POA
    | dev | research-article       | True     | False          | author_publication_email_POA
    | dev | research-article       | False    | True           | author_publication_email_VOR_after_POA
    | dev | research-article       | False    | False          | author_publication_email_VOR_no_POA
    | dev | research-article       | False    | None           | author_publication_email_VOR_no_POA

    