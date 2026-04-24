# Language: en
Feature: Login


  @smoke @P0
  Scenario: Successful login
    # Priority: P1 | Risk Score: 4.25 | Endpoint: POST /api/auth/login
    Given I have a valid username and password
    When I POST to /api/auth/login
    Then the response status code should be 200
    And the response should include a valid access token


  @regression @P1
  Scenario: Invalid login credentials
    # Priority: P1 | Risk Score: 4.04 | Endpoint: POST /api/auth/login
    Given I have an invalid username or password
    When I POST to /api/auth/login
    Then the response status code should be 401
    And the response should include an error message


  @regression @P2
  Scenario: Account lockout after 3 failed login attempts
    # Priority: P2 | Risk Score: 3.60 | Endpoint: POST /api/auth/login
    Given I have a valid username and password
    And I have failed to login 3 times
    When I POST to /api/auth/login
    Then the response status code should be 423
    And the response should include an account lockout error message


  @regression @P2
  Scenario: Successful registration
    # Priority: P2 | Risk Score: 3.40 | Endpoint: POST /api/auth/register
    Given I have a valid username and password
    When I POST to /api/auth/register
    Then the response status code should be 201
    And the response should include a success message


  @regression @P2
  Scenario: Duplicate registration
    # Priority: P2 | Risk Score: 3.04 | Endpoint: POST /api/auth/register
    Given I have a valid username and password
    And the username is already registered
    When I POST to /api/auth/register
    Then the response status code should be 400
    And the response should include a duplicate registration error message


  @regression @P2
  Scenario: Successful logout
    # Priority: P2 | Risk Score: 3.56 | Endpoint: POST /api/auth/logout
    Given I am logged in
    When I POST to /api/auth/logout
    Then the response status code should be 200
    And the response should include a success message


  @smoke @P1
  Scenario: Successful token refresh
    # Priority: P1 | Risk Score: 4.25 | Endpoint: POST /api/auth/refresh
    Given I have a valid refresh token
    When I POST to /api/auth/refresh
    Then the response status code should be 200
    And the response should include a new access token


  @regression @P2
  Scenario: Invalid token refresh
    # Priority: P2 | Risk Score: 3.66 | Endpoint: POST /api/auth/refresh
    Given I have an invalid refresh token
    When I POST to /api/auth/refresh
    Then the response status code should be 401
    And the response should include an error message
